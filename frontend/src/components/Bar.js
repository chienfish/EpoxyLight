import { useState } from "react";
import "../styles/Bar.css";
import { FaRegHandshake } from "react-icons/fa6";


const Bar = () => {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="bar">
      <div className="bar-content">
        <a href="/" className="bar-logo">
          <FaRegHandshake className="book-icon" />
        </a>

        <div className={`bar-links ${menuOpen ? "open" : ""}`}>
          <a href="/">Home</a>
          <a href="/create">Create</a>
          <a href="/status">Status</a>
          <a href="/history">History</a>
        </div>

        <div className="hamburger" onClick={() => setMenuOpen(!menuOpen)}>
          <div>&#9776;</div>
        </div>
      </div>
    </div>
  );
};

export default Bar;
