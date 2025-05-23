import React from 'react';
import './Message.css';
import { Message as MessageType, AiTabType, AiMessageContent } from './ChatInterface';
import MarkdownRenderer from './MarkdownRenderer';

interface MessageProps {
  message: MessageType;
  onTabChange: (messageId: string, tab: AiTabType) => void; // Add this prop
}

const Message: React.FC<MessageProps> = ({ message, onTabChange }) => {
  const { id, role, content, activeTab, availableTabs, isStreaming } = message;

  const renderContent = () => {
    if (role === 'user') {
      return <div className="message-text">{content as string}</div>;
    }

    // AI Message
    const aiContent = content as AiMessageContent;
    const currentActiveTab = activeTab || 'chat'; // Default to chat if somehow undefined
    const tabContent = aiContent[currentActiveTab] || '';
    
    // Add streaming indicator to tab content if message is streaming
    const displayContent = isStreaming && (!tabContent || tabContent.length < 5) // Only show if content is short or empty
        ? tabContent + "..." 
        : tabContent;

    return <MarkdownRenderer content={displayContent} />;
  };

  const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

  return (
    <div className={`message ${role === 'user' ? 'user-message' : 'ai-message'}`}>
      <div className="message-avatar">
        {role === 'user' ? '👤' : '🤖'}
      </div>
      <div className="message-content-wrapper">
        {role === 'ai' && availableTabs && availableTabs.length > 0 && (
          <div className="tab-buttons">
            {(availableTabs as AiTabType[]).map((tabName) => {
              // Ensure content exists for the tab or it's the default 'chat' tab or it's the active tab
              const aiContent = content as AiMessageContent;
              const hasContent = !!aiContent[tabName];
              const isReporterAndActive = tabName === 'reporter' && activeTab === 'reporter';

              // Show tab if it's chat, or has content, or it's reporter and active (to ensure it appears as per requirement)
              if (tabName === 'chat' || hasContent || isReporterAndActive || availableTabs.includes(tabName)) {
                return (
                  <button
                    key={tabName}
                    className={`tab-button ${activeTab === tabName ? 'active' : ''}`}
                    onClick={() => onTabChange(id, tabName)}
                  >
                    {capitalize(tabName)}
                  </button>
                );
              }
              return null;
            })}
          </div>
        )}
        <div className="message-content">
          {renderContent()}
        </div>
      </div>
    </div>
  );
};

export default Message;
