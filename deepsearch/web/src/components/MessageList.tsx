import React from 'react';
import './MessageList.css';
import MessageComponent from './Message'; // Renamed to avoid conflict
import { Message as MessageType, AiTabType } from './ChatInterface';

interface MessageListProps {
  messages: MessageType[];
  onTabChange: (messageId: string, tab: AiTabType) => void; // Add this prop
}

const MessageList: React.FC<MessageListProps> = ({ messages, onTabChange }) => {
  if (messages.length === 0) {
    return (
      <div className="message-list empty">
        <div className="empty-state">
          <h2>Welcome to DeepSearch</h2>
          <p>Ask a question to start a conversation!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((message) => (
        <MessageComponent
          key={message.id}
          message={message}
          onTabChange={onTabChange} // Pass it down
        />
      ))}
    </div>
  );
};

export default MessageList;
