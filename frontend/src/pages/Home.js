import React from "react";
import "../styles/Home.css";
import Bar from "../components/Bar";
import Mem1 from "../assets/1.jpg";
import Mem2 from "../assets/2.jpg";
import Mem3 from "../assets/3.jpg";
import Mem4 from "../assets/4.jpg";

const teamMembers = [
  {
    name: "林芊妤",
    role: "Frontend",
    image: Mem2,
  },
  {
    name: "尤梓薰",
    role: "Database",
    image: Mem1,
  },
  {
    name: "許米棋",
    role: "Backend",
    image: Mem3,
  },
  {
    name: "許博睿",
    role: "Quality Assurance",
    image: Mem4,
  },
];

const Home = () => {
  return (
    <>
      <Bar />
      <div className="home-container">
        <h1 className="epoxy-title">EPOXY-LIGHT</h1>

        <section className="intro-section">
          <div className="intro-text">
            <h2>
              什麼是 <strong>Epoxy-Light</strong>？
            </h2>
            <ul>
              <li>🟧 一套模擬 2PC 的資料庫原子交易協調器</li>
              <li>🟨 同時操作 MySQL 與 MongoDB，確保資料一致性</li>
            </ul>
          </div>
          <div className="intro-image">
            <img
              src="https://histock.tw/uploadimages/38589/Trading-Strategies-Cover-crop1.jpg"
              alt="transaction themed"
            />
          </div>
        </section>

        <section className="team">
          <h2>Our Teams</h2>
          <div className="team-grid">
            {teamMembers.map((member, index) => (
              <div className="member-card" key={index}>
                <img src={member.image} alt={member.name} />
                <h3>{member.name}</h3>
                <p>{member.role}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </>
  );
};

export default Home;
