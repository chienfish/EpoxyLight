# Epoxy Light

Epoxy Light is a lightweight **cross-database transaction coordinator** designed to maintain consistency across heterogeneous databases.

The system simulates a simplified **Two-Phase Commit (2PC)** protocol to coordinate transactions between **MySQL** and **MongoDB**, ensuring that operations either succeed together or fail together.

This project is inspired by the Epoxy system proposed in the VLDB paper on cross-database ACID transactions.

<p align="center">
  <a href="#features">Features</a> •
  <a href="#system-architecture">System Architecture</a> •
  <a href="#transaction-workflow">Transaction Workflow</a> •
  <a href="#database-design">Database Design</a> •
  <a href="#api-endpoints">API Endpoints</a> •
  <a href="#tech-stack">Tech Stack</a> •
  <a href="#references">References</a>
</p>

<br>

[![Watch the demo](https://img.youtube.com/vi/Di0-Dj4irCs/maxresdefault.jpg)](https://youtu.be/Di0-Dj4irCs)

<br>

---

<!-- Features -->
## Features

- Cross-database transaction coordination
- Simplified **Two-Phase Commit (2PC)**
- RESTful API for transaction control
- **Rollback mechanism** for failed transactions
- Transaction logging for consistency tracking
- Support for **MySQL and MongoDB**

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- System Architecture -->
## System Architecture

The system uses a **Flask-based transaction coordinator** to manage operations across multiple databases.

Client
│
▼
Flask REST API (Coordinator)
│
├── MySQL (Orders)
└── MongoDB (Products / Inventory)
│
▼
Transaction Log


The coordinator ensures that both databases follow the same transaction state.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- Transaction Workflow -->
## Transaction Workflow

The system follows a simplified **2PC-style workflow**:

### 1. Begin
- Create a new `transaction_id`
- Record transaction metadata in the log

### 2. Prepare
- Validate order request
- Write data to staging tables
- Mark databases as ready

### 3. Commit
- Move staging data to production tables
- Mark transaction as successful

### 4. Rollback
- Remove staged changes
- Cancel the transaction

These steps ensure both databases maintain consistent states during transactions.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- Database Design -->
## Database Design

### MySQL

Tables used for order management:

- `orders`
- `orders_staging`

The staging table temporarily stores transaction data before commit.

### MongoDB

Collections used for product inventory:

- `products`
- `products_staging`
- `transaction_log`

The transaction log records the status and progress of each transaction.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- API Endpoints -->
## API Endpoints

| Endpoint | Description |
|--------|-------------|
| `/begin` | Start a new transaction |
| `/prepare` | Validate and stage data |
| `/commit` | Finalize the transaction |
| `/rollback` | Cancel the transaction |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- Tech Stack -->
## Tech Stack

- ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
- ![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
- ![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
- ![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
- ![REST API](https://img.shields.io/badge/REST_API-02569B?style=for-the-badge)
- ![Distributed Systems](https://img.shields.io/badge/Distributed_Systems-Transactions-black?style=for-the-badge)
- ![Two Phase Commit](https://img.shields.io/badge/2PC-Transaction_Protocol-purple?style=for-the-badge)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- References -->
## References

This project is inspired by the following research work:

Zaharia, Matei, et al.  
**"Epoxy: ACID Transactions Across Diverse Data Stores."**  
Proceedings of the VLDB Endowment, 2023.  

https://people.eecs.berkeley.edu/~matei/papers/2023/vldb_epoxy.pdf

<p align="right">(<a href="#readme-top">back to top</a>)</p>
