import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import os

class TrafficPredictor:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.is_trained = False

    def prepare_data(self, traffic_df, roads_df, neighborhoods_df):
        # Merge data to create features
        # Features: FromID, ToID, Distance, Capacity, Condition, From_Population, To_Population, Time_Period
        
        data = []
        time_periods = {
            "morning": "MorningPeak(veh/h)",
            "afternoon": "Afternoon(veh/h)",
            "evening": "Evening Peak(veh/h)",
            "night": "Night(veh/h)"
        }
        time_mapping = {"morning": 0, "afternoon": 1, "evening": 2, "night": 3}

        for _, row in traffic_df.iterrows():
            road_id = str(row["RoadID"])
            if "-" not in road_id: continue
            parts = road_id.split("-")
            if len(parts) != 2: continue
            from_id, to_id = parts[0], parts[1]
            
            # Get road features
            road_info = roads_df[(roads_df["FromID"] == from_id) & (roads_df["ToID"] == to_id)]
            if road_info.empty:
                road_info = roads_df[(roads_df["FromID"] == to_id) & (roads_df["ToID"] == from_id)]
            
            if road_info.empty: continue
            
            dist = road_info.iloc[0]["Distance(km)"]
            cap = road_info.iloc[0]["Current Capacity(vehicles/hour)"]
            cond = road_info.iloc[0]["Condition(1-10)"]
            
            # Get population features (facility nodes like F1/F2 won't be in neighborhoods; use 0)
            from_pop_r = neighborhoods_df[neighborhoods_df["ID"].astype(str) == str(from_id)]
            to_pop_r = neighborhoods_df[neighborhoods_df["ID"].astype(str) == str(to_id)]
            from_pop = from_pop_r.iloc[0]["Population"] if not from_pop_r.empty else 0
            to_pop = to_pop_r.iloc[0]["Population"] if not to_pop_r.empty else 0
            
            for period, col in time_periods.items():
                flow = row[col]
                data.append([from_id, to_id, dist, cap, cond, from_pop, to_pop, time_mapping[period], flow])
        
        df = pd.DataFrame(data, columns=["FromID", "ToID", "Distance", "Capacity", "Condition", "FromPop", "ToPop", "TimePeriod", "Flow"])
        
        # Convert IDs to numeric for ML model
        df['FromID'] = pd.factorize(df['FromID'])[0]
        df['ToID'] = pd.factorize(df['ToID'])[0]
        
        return df

    def train(self, traffic_df, roads_df, neighborhoods_df):
        # Store the original IDs to create a mapping for prediction
        self.raw_df = self.prepare_data(traffic_df, roads_df, neighborhoods_df)
        
        # We need to handle the mapping of string IDs to the numeric factors used in training
        # Let's simplify: just use hash or a simple mapping
        self.id_map = {}
        all_ids = set(traffic_df["RoadID"].str.split("-").str[0].unique()) | set(traffic_df["RoadID"].str.split("-").str[1].unique())
        for i, original_id in enumerate(sorted(list(all_ids))):
            self.id_map[str(original_id)] = i

        # Re-prepare data with the mapping
        data = []
        time_periods = {"morning": "MorningPeak(veh/h)", "afternoon": "Afternoon(veh/h)", "evening": "Evening Peak(veh/h)", "night": "Night(veh/h)"}
        time_mapping = {"morning": 0, "afternoon": 1, "evening": 2, "night": 3}

        for _, row in traffic_df.iterrows():
            road_id = str(row["RoadID"])
            parts = road_id.split("-")
            if len(parts) != 2: continue
            u_id, v_id = parts[0], parts[1]
            
            road_info = roads_df[(roads_df["FromID"].astype(str) == u_id) & (roads_df["ToID"].astype(str) == v_id)]
            if road_info.empty:
                road_info = roads_df[(roads_df["FromID"].astype(str) == v_id) & (roads_df["ToID"].astype(str) == u_id)]
            if road_info.empty: continue
            
            dist = road_info.iloc[0]["Distance(km)"]
            cap = road_info.iloc[0]["Current Capacity(vehicles/hour)"]
            cond = road_info.iloc[0]["Condition(1-10)"]
            
            from_pop_row = neighborhoods_df[neighborhoods_df["ID"].astype(str) == u_id]
            to_pop_row = neighborhoods_df[neighborhoods_df["ID"].astype(str) == v_id]
            # Facility nodes (F1, F2, etc.) are not in neighborhoods_df; use 0 as fallback
            from_pop = from_pop_row.iloc[0]["Population"] if not from_pop_row.empty else 0
            to_pop = to_pop_row.iloc[0]["Population"] if not to_pop_row.empty else 0
            
            for period, col in time_periods.items():
                flow = row[col]
                data.append([self.id_map[u_id], self.id_map[v_id], dist, cap, cond, from_pop, to_pop, time_mapping[period], flow])

        train_df = pd.DataFrame(data, columns=["FromID", "ToID", "Distance", "Capacity", "Condition", "FromPop", "ToPop", "TimePeriod", "Flow"])
        X = train_df.drop("Flow", axis=1)
        y = train_df["Flow"]
        
        self.model.fit(X, y)
        self.is_trained = True

    def predict(self, from_id, to_id, dist, cap, cond, from_pop, to_pop, time_period_str):
        if not self.is_trained:
            return None
        
        # Map string IDs to numeric
        u_numeric = self.id_map.get(str(from_id), -1)
        v_numeric = self.id_map.get(str(to_id), -1)
        
        time_mapping = {"morning": 0, "afternoon": 1, "evening": 2, "night": 3}
        time_val = time_mapping.get(time_period_str.lower(), 0)
        
        features = np.array([[u_numeric, v_numeric, dist, cap, cond, from_pop, to_pop, time_val]])
        prediction = self.model.predict(features)[0]
        return prediction

def get_predictor(data_files):
    predictor = TrafficPredictor()
    traffic_df = pd.read_excel(data_files["traffic_flow"])
    roads_df = pd.read_excel(data_files["existing_roads"])
    neighborhoods_df = pd.read_excel(data_files["neighborhoods"])
    predictor.train(traffic_df, roads_df, neighborhoods_df)
    return predictor
