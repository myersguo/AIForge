import React, { useState, useRef, useEffect } from 'react';
import './InputArea.css';

interface InputAreaProps {
  onSendMessage: (text: string) => void;
  isLoading: boolean;
   isStreaming?: boolean; // 新增
  onCancelStream?: () => void; // 新增
}

const InputArea: React.FC<InputAreaProps> = ({ onSendMessage, isLoading,  isStreaming, 
  onCancelStream  }) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Auto-focus the input when the component mounts
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    adjustTextareaHeight();
  };

  return (
    <form className="input-area" onSubmit={handleSubmit}>
      <textarea
        ref={textareaRef}
        className="message-input"
        value={message}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="Type your message..."
        disabled={isLoading}
        rows={1}
      />
      {isStreaming && onCancelStream && (
        <button 
          onClick={onCancelStream}
          className="cancel-button"
          type="button"
        >
          Cancel
        </button>
      )}
      <button 
        type="submit" 
        className="send-button"
        disabled={!message.trim() || isLoading}
      >
         {isStreaming ? 'Streaming...' : isLoading ? (
            <span className="loading-spinner"></span> 
         )
         : 'Send'}
      </button>
    </form>
  );
};

export default InputArea;
