import React, { useState, useEffect, useRef, FormEvent } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';
import './App.css';

interface MessageSource {
  title: string;
  url: string;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  content: string;
  sources?: MessageSource[];
  type?: 'text' | 'error' | 'loading_placeholder';
}

interface SseSourcesData extends Array<MessageSource> {}
type SseAnswerChunkData = string;
interface SseErrorData {
  message: string;
  status_code?: number;
  type?: string;
  code?: string;
  param?: string;
  details?: string;
}

const App: React.FC = () => {
  const [inputValue, setInputValue] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort("Component unmounting");
      }
    };
  }, []);

  // 处理引用点击事件
  const handleCitationClick = (sources: MessageSource[], citationIndex: number) => {
    const source = sources[citationIndex - 1]; // citation从1开始，数组从0开始
    if (source && source.url) {
      window.open(source.url, '_blank', 'noopener,noreferrer');
    }
  };

  // 渲染带有引用链接的内容
  const renderContentWithCitations = (content: string, sources: MessageSource[] = []) => {
    if (!sources.length) {
      return <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>{content}</ReactMarkdown>;
    }

    // 将 [citation:n] 替换为可点击的链接
    const processedContent = content.replace(/\[citation:(\d+)\]/g, (match, num) => {
      const citationIndex = parseInt(num, 10);
      const source = sources[citationIndex - 1];
      if (source) {
        return `[${source.title}](#citation-${citationIndex})`;
      }
      return match;
    });

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          a: ({href, children, ...props}) => {
            if (href?.startsWith('#citation-')) {
              const citationIndex = parseInt(href.replace('#citation-', ''), 10);
              return (
                <span
                  className="citation-link"
                  onClick={(e) => {
                    e.preventDefault();
                    handleCitationClick(sources, citationIndex);
                  }}
                  {...props}
                >
                  [{children}]
                </span>
              );
            }
            return <a href={href} target="_blank" rel="noopener noreferrer" {...props}>{children}</a>;
          }
        }}
      >
        {processedContent}
      </ReactMarkdown>
    );
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userQuery = inputValue;
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      content: userQuery,
      type: 'text',
    };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    const aiMessageId = `ai-${Date.now()}`;
    setMessages(prev => [
      ...prev,
      {
        id: aiMessageId,
        sender: 'ai',
        content: '',
        sources: [],
        type: 'loading_placeholder',
      },
    ]);

    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    try {
      const response = await fetch('http://localhost:8000/search/summary', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ query: userQuery, top_k: 5 }),
        signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error ${response.status}: ${errorText || response.statusText}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();

        if (done) {
          setMessages(prev => prev.map(msg =>
              msg.id === aiMessageId && msg.type === 'loading_placeholder' && msg.content === ''
              ? { ...msg, content: '[Stream ended without content]', type: 'text' }
              : msg
          ));
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        let eventBoundary = buffer.indexOf('\n\n');

        while (eventBoundary !== -1) {
          const singleEventString = buffer.substring(0, eventBoundary);
          buffer = buffer.substring(eventBoundary + 2);

          let eventName = 'message';
          let eventDataJson = '';

          singleEventString.split('\n').forEach(line => {
            if (line.startsWith('event: ')) {
              eventName = line.substring('event: '.length).trim();
            } else if (line.startsWith('data: ')) {
              eventDataJson = line.substring('data: '.length).trim();
            }
          });

          if (eventDataJson) {
            try {
              const parsedData = JSON.parse(eventDataJson);

              setMessages(prevMessages =>
                prevMessages.map(msg => {
                  if (msg.id === aiMessageId && msg.sender === 'ai') {
                    let newContent = msg.content;
                    let newSources = msg.sources || [];
                    let newType = msg.type === 'loading_placeholder' ? 'text' : msg.type;

                    switch (eventName) {
                      case 'sources':
                        newSources = parsedData as SseSourcesData;
                        break;
                      case 'answer_chunk':
                        newContent += parsedData as SseAnswerChunkData;
                        if (msg.type === 'loading_placeholder' && newContent.trim() !== '') {
                            newType = 'text';
                        }
                        break;
                      case 'error':
                        const errorInfo = parsedData as SseErrorData;
                        console.error('SSE Error Event:', errorInfo);
                        newContent += `\n⚠️ Error: ${errorInfo.message}${errorInfo.status_code ? ` (Status: ${errorInfo.status_code})` : ''}`;
                        newType = 'error';
                        setIsLoading(false);
                        if (reader && !signal.aborted) {
                            reader.cancel('SSE error event received').catch(e => console.warn("Error cancelling reader:", e));
                        }
                        break;
                      case 'done':
                        setIsLoading(false);
                        if (msg.type === 'loading_placeholder' && newContent.trim() === '') {
                            newContent = "[No content generated]";
                            newType = 'text';
                        }
                        break;
                      default:
                        console.warn(`Unknown SSE event: ${eventName}`, parsedData);
                    }
                    return { ...msg, content: newContent, sources: newSources, type: newType };
                  }
                  return msg;
                })
              );
            } catch (e) {
              console.error('Failed to parse SSE event data or update state:', eventDataJson, e);
              setMessages(prev => prev.map(msg =>
                  msg.id === aiMessageId && msg.sender === 'ai'
                  ? { ...msg, content: msg.content + `\n[Error processing stream data. Check console.]`, type: 'error' }
                  : msg
              ));
              setIsLoading(false);
              if (reader && !signal.aborted) {
                reader.cancel('SSE parsing error').catch(err => console.warn("Error cancelling reader:", err));
              }
            }
          }
          eventBoundary = buffer.indexOf('\n\n');
        }
      }
    } catch (error: any) {
      console.error('Chat handleSubmit error:', error);
      if (error.name === 'AbortError') {
        console.log('Fetch aborted.');
      } else {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === aiMessageId && msg.sender === 'ai'
              ? { ...msg, content: `Failed to get response: ${error.message}`, type: 'error' }
              : msg
          )
        );
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="chat-app">
      <header className="app-header">
        <h1>AI Search</h1>
      </header>
      <div className="chat-window">
        <div className="message-list">
          {messages.map(msg => (
            <div key={msg.id} className={`message-bubble ${msg.sender} ${msg.type || ''}`}>
              <div className="message-content">
                {msg.type === 'loading_placeholder' && msg.sender === 'ai' && !msg.content ? (
                  <div className="typing-indicator">
                    <span></span><span></span><span></span>
                  </div>
                ) : (
                  <div className="markdown-content">
                    {renderContentWithCitations(msg.content, msg.sources)}
                  </div>
                )}
              </div>
              {/*{msg.sources && msg.sources.length > 0 && msg.type !== 'loading_placeholder' && (*/}
              {/*  <div className="message-sources">*/}
              {/*    <div className="sources-title">Sources:</div>*/}
              {/*    <div className="sources-list">*/}
              {/*      {msg.sources.map((source, index) => (*/}
              {/*        <div key={index} className="source-item">*/}
              {/*          <span className="source-number">[{index + 1}]</span>*/}
              {/*          <a*/}
              {/*            href={source.url}*/}
              {/*            target="_blank"*/}
              {/*            rel="noopener noreferrer"*/}
              {/*            className="source-link"*/}
              {/*            title={source.url}*/}
              {/*          >*/}
              {/*            {source.title}*/}
              {/*          </a>*/}
              {/*        </div>*/}
              {/*      ))}*/}
              {/*    </div>*/}
              {/*  </div>*/}
              {/*)}*/}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>
      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={inputValue}
          onChange={e => setInputValue(e.target.value)}
          placeholder="Ask AI..."
          disabled={isLoading}
          aria-label="Chat input"
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
};

export default App;