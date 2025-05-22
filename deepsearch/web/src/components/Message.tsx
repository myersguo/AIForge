import React from 'react';
import './Message.css';
import { Message as MessageType } from './ChatInterface';
import MarkdownRenderer from './MarkdownRenderer';

interface MessageProps {
  message: MessageType;
}

const Message: React.FC<MessageProps> = ({ message }) => {
  const { role, content } = message;
  
  return (
    <div className={`message ${role === 'user' ? 'user-message' : 'ai-message'}`}>
      <div className="message-avatar">
        {role === 'user' ? '👤' : '🤖'}
      </div>
      <div className="message-content">
        {role === 'user' ? (
          <div className="message-text">{content}</div>
        ) : (
          <MarkdownRenderer content={content} />
        )}
      </div>
    </div>
  );
};

export default Message;
