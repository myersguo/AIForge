import React from 'react';
import './MessageList.css';
import Message from './Message';
import { Message as MessageType } from './ChatInterface';

interface MessageListProps {
  messages: MessageType[];
}

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
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
        <Message key={message.id} message={message} />
      ))}
    </div>
  );
};

export default MessageList;
