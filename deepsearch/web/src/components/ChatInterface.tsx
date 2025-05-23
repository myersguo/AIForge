// ./ChatInterface.tsx
import React, { useState, useRef, useEffect } from 'react';
import './ChatInterface.css';
import MessageList from './MessageList';
import InputArea from './InputArea';

export type AiTabType = 'chat' | 'search' | 'reporter';

export interface AiMessageContent {
  chat: string;
  search: string;
  reporter: string;
}

export interface Message {
  id: string;
  role: 'user' | 'ai';
  content: string | AiMessageContent; // User content is string, AI content is AiMessageContent
  timestamp: number;
  isStreaming?: boolean;
  activeTab?: AiTabType; // Only for AI messages
  availableTabs?: AiTabType[]; // Tabs that have content or are expected
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isLoading || isStreaming) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setIsStreaming(true);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(
        'http://localhost:8081/api/query_stream',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify({ query: text }),
          signal: abortControllerRef.current.signal,
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();
      const aiMessageId = (Date.now() + 1).toString();
      const initialAiMessage: Message = {
        id: aiMessageId,
        role: 'ai',
        content: { chat: '', search: '', reporter: '' },
        timestamp: Date.now(),
        isStreaming: true,
        activeTab: 'chat',
        availableTabs: ['chat'],
      };

      setMessages((prev) => [...prev, initialAiMessage]);
      setIsLoading(false); 

      let buffer = '';
      let continueReadingStream = true; // For ESLint no-constant-condition

      while (continueReadingStream) {
        const { done, value } = await reader.read();

        if (done) {
          continueReadingStream = false;
          break; 
        }

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; 

        for (const line of lines) {
          const trimmedLine = line.trim();

          if (trimmedLine.startsWith('event:')) {
            continue;
          }

          if (trimmedLine.startsWith('data:')) {
            try {
              const jsonData = trimmedLine.slice(5).trim();
              if (jsonData === '') continue;

              const data = JSON.parse(jsonData); 

              if (data.error) {
                throw new Error(data.error);
              }

              if (data.chunk !== undefined) {
                setMessages((prevMessages) =>
                  prevMessages.map((msg) => {
                    if (msg.id === aiMessageId && msg.role === 'ai') {
                      const newContent = { ...(msg.content as AiMessageContent) };
                      let newActiveTab = msg.activeTab;
                      const newAvailableTabs = [...(msg.availableTabs || ['chat'])];

                      switch (data.type) {
                        case 'search_result':
                          newContent.search = (newContent.search || '') + (data.chunk || '');
                          if (!newAvailableTabs.includes('search')) {
                            newAvailableTabs.push('search');
                          }
                          break;
                        case 'reporter_result':
                          newContent.reporter = (newContent.reporter || '') + (data.chunk || '');
                          if (!newAvailableTabs.includes('reporter')) {
                            newAvailableTabs.push('reporter');
                          }
                          newActiveTab = 'reporter'; 
                          break;
                        case 'stream':
                        case 'intermediate':
                        case 'final': 
                        default: 
                          newContent.chat = (newContent.chat || '') + (data.chunk || '');
                          if (!newAvailableTabs.includes('chat')) {
                             newAvailableTabs.push('chat');
                          }
                          break;
                      }

                      return {
                        ...msg,
                        content: newContent,
                        activeTab: newActiveTab,
                        availableTabs: newAvailableTabs,
                      };
                    }
                    return msg;
                  })
                );
              }
              if (data.done) {
                setMessages((prev) =>
                    prev.map((msg) =>
                        msg.id === aiMessageId ? { ...msg, isStreaming: false, activeTab: (data.type === 'reporter_result' ? 'reporter' : msg.activeTab) } : msg
                    )
                );
              }
            } catch (parseError) {
              console.error('Error parsing JSON:', parseError, 'Data:', trimmedLine);
            }
          }
        }
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMessageId ? { ...msg, isStreaming: false } : msg
        )
      );

    } catch (error: unknown) {
      console.error('Error in handleSendMessage:', error);
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Request was aborted by user');
        // Update the last AI message to reflect interruption
        setMessages((prev) =>
            prev.map((m) => {
                    const content = m.content as AiMessageContent;
                    const activeTab = m.activeTab || 'chat';
                    content[activeTab] = (content[activeTab] || "") + "\n[Response interrupted by user]";
                    return { ...m, isStreaming: false, content };
            })
        );
      } else {
        const errorMessageContent: AiMessageContent = {
            chat: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
            search: '',
            reporter: '',
        };
        const errorMessage: Message = {
            id: (Date.now() + 2).toString(),
            role: 'ai',
            content: errorMessageContent,
            timestamp: Date.now(),
            activeTab: 'chat',
            availableTabs: ['chat'],
            isStreaming: false,
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } finally {
      setIsLoading(false);
      setIsStreaming(false); 
      if (abortControllerRef.current) {
        abortControllerRef.current = null;
      }
    }
  };

  const handleCancelStream = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort(); 
    }
    setIsLoading(false);
    setIsStreaming(false);
  };

  const handleTabChange = (messageId: string, tab: AiTabType) => {
    setMessages((prevMessages) =>
      prevMessages.map((msg) =>
        msg.id === messageId && msg.role === 'ai' ? { ...msg, activeTab: tab } : msg
      )
    );
  };


  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return (
    <div className="chat-interface">
      <div className="messages-container" ref={messagesContainerRef}>
        <MessageList messages={messages} onTabChange={handleTabChange} />
        <div ref={messagesEndRef} />
      </div>
      <InputArea
        onSendMessage={handleSendMessage}
        isLoading={isLoading} 
        isStreaming={isStreaming} 
        onCancelStream={handleCancelStream}
      />
    </div>
  );
};

export default ChatInterface;
