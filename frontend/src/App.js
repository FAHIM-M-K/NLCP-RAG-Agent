import React, { useState, useRef, useEffect } from 'react';
import './App.css'; 

function App() {
  const [messages, setMessages] = useState([
    {
      sender: 'agent',
      text: (
        <div className="welcome-message">
          <h3>Here are some questions you can ask:</h3>
          <ul>
            <li>"What are the top five portfolios of our wealth members?"</li>
            <li>"Give me the breakup of portfolio values per relationship manager."</li>
            <li>"Tell me the top relationship managers in my firm."</li>
            <li>"Which clients are the highest holders of [specific stock]?"</li>
          </ul>
        </div>
      )
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  
  const API_URL = process.env.REACT_APP_API_URL;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto'; 
      textarea.style.height = `${textarea.scrollHeight}px`; 
    }
  }, [input]);

  const sendMessage = async () => {
    if (input.trim() === '' || loading) return;

    const userMessage = { sender: 'user', text: input.trim() };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setInput('');
    setLoading(true);

    try {
      
      const response = await fetch(`${API_URL}query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ message: userMessage.text }), 
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Backend Error Response:', errorData);
        throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      let agentResponseContent;

      if (data && typeof data.response === 'object') {
        agentResponseContent = <pre>{JSON.stringify(data.response, null, 2)}</pre>;
      } else if (data && data.response) {
        agentResponseContent = data.response;
      } else {
        agentResponseContent = "No valid response received from the agent.";
      }

      const agentMessage = { sender: 'agent', text: agentResponseContent };
      setMessages((prevMessages) => [...prevMessages, agentMessage]);

    } catch (error) {
      const errorMessage = { sender: 'agent', text: `Error: ${error.message}` };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
      console.error('Frontend Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="App">
      <header className="app-title">
        Data Query RAG Agent
      </header>
      <div className="chat-container">
        <div className="messages-display">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.sender}`}>
              <div className="message-content">{msg.text}</div>
            </div>
          ))}
          {loading && (
            <div className="message agent">
              <div className="message-content thinking-bubble">Thinking...</div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className="input-area-container">
          <div className="input-area">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question..."
              rows="1"
              disabled={loading}
            />
            <button onClick={sendMessage} disabled={loading || !input.trim()}>
              ↑
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;