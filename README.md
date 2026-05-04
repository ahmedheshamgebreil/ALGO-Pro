# Smart City Transportation Network Optimization

This project simulates and optimizes transportation networks for smart cities, with a focus on Cairo, Egypt. It implements various algorithms to find optimal routes, simulate traffic conditions, and optimize public transportation schedules.

## 🌟 CSE112 Bonus Features Implemented

This repository includes all the required features for the **CSE112 Bonus (10 Marks)**:

1. **Early Submission (Week 13) (2 Marks)**: Submitted ahead of the deadline.
2. **AI Tools & Technologies (2 Marks)**: Utilized AI assistance for code optimization, debugging, and documentation.
3. **Enhanced Visualization & UI (2 Marks)**: Improved Streamlit UI with side-by-side algorithm comparison and interactive Folium maps.
4. **Deployment & Engineering (3 Marks)**: 
   - **Docker Containerization**: The project is fully containerized using Docker (`Dockerfile` and `docker-compose.yml` included).
   - **Live Web App**: Deployed and accessible at [https://ahmedheshamgebreil-algo-pro-app-updated-rnshmq.streamlit.app/](https://ahmedheshamgebreil-algo-pro-app-updated-rnshmq.streamlit.app/)
5. **GitHub Repo & LinkedIn Post (1 Mark)**: Well-structured repository with this comprehensive README and a draft for the LinkedIn post.

### 🚀 Key Additions

- **ML-Based Traffic Prediction**: Uses `scikit-learn` (RandomForestRegressor) trained on temporal traffic data (Morning, Afternoon, Evening, Night) to forecast congestion based on road capacity, distance, condition, and district population.
- **Algorithm Comparison Visualizer**: A side-by-side race animation comparing Dijkstra's Algorithm and A* Search, demonstrating how A* explores fewer nodes by utilizing a heuristic.

## 🛠️ Installation & Setup

### Option 1: Using Docker (Recommended)

1. Ensure you have Docker and Docker Compose installed.
2. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Smart_City_Transportation_Network_Optimization_Project.git
   cd Smart_City_Transportation_Network_Optimization_Project
   ```
3. Build and run the container:
   ```bash
   docker-compose up --build
   ```
4. Open your browser and navigate to `http://localhost:8501`.

### Option 2: Manual Installation

1. Clone the repository.
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   streamlit run app_updated.py
   ```

## 📊 Features

- **Multi-modal Transportation**: Simulate routes using cars, buses, metro, or emergency vehicles.
- **Traffic-aware Routing**: Consider traffic conditions at different times of day.
- **Emergency Vehicle Simulation**: Simulate the impact of emergency vehicles on regular traffic.
- **Network Analysis**: View and analyze the transportation network graph.
- **MST Visualization**: Visualize the Minimum Spanning Tree for optimal network design.
- **Transit Scheduling**: Optimize public transportation schedules and routes.
- **ML Traffic Prediction**: Forecast congestion levels using machine learning.
- **Algorithm Comparison**: Visual race between Dijkstra and A*.

## 📝 LinkedIn Post Draft

Here is a draft for your LinkedIn post to showcase the project:

```text
🚀 Excited to share my latest project: Smart City Transportation Network Optimization! 🏙️

As part of my CSE112 coursework, I developed a comprehensive transportation simulator focusing on Cairo, Egypt. The goal was to optimize routes, manage traffic flow, and improve public transit efficiency using advanced algorithms.

Key features include:
✅ Multi-modal routing (Car, Bus, Metro, Emergency)
✅ Traffic-aware pathfinding using Dijkstra's Algorithm
✅ Emergency vehicle routing with A* Search
✅ Minimum Spanning Tree (MST) for network design
✅ Public transit schedule optimization

🌟 Bonus Features Implemented:
🤖 ML-Based Traffic Prediction: Used scikit-learn (Random Forest) to forecast congestion based on temporal data, road conditions, and district population.
🏎️ Algorithm Race Visualizer: Built an interactive side-by-side animation comparing Dijkstra vs. A* to demonstrate the efficiency of heuristics!
🐳 Docker Containerization: Fully containerized the app for seamless deployment.
🌐 Live Web App: Deployed the Streamlit dashboard for anyone to try out!

Check out the live demo here: [https://ahmedheshamgebreil-algo-pro-app-updated-rnshmq.streamlit.app/](https://ahmedheshamgebreil-algo-pro-app-updated-rnshmq.streamlit.app/)
Explore the code on GitHub: [https://github.com/ahmedheshamgebreil/ALGO-Pro](https://github.com/ahmedheshamgebreil/ALGO-Pro)

A big thank you to my professors and peers for the support. Let me know what you think in the comments! 👇

#SmartCity #Transportation #Algorithms #MachineLearning #Python #Streamlit #Docker #DataScience #CSE112
```

## 📄 License

This project is licensed under the MIT License.
