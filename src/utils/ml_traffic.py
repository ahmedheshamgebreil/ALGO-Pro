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
            from_id, to_id = map(int, road_id.split("-"))
            
            # Get road features
            road_info = roads_df[(roads_df["FromID"] == from_id) & (roads_df["ToID"] == to_id)]
            if road_info.empty:
                road_info = roads_df[(roads_df["FromID"] == to_id) & (roads_df["ToID"] == from_id)]
            
            if road_info.empty: continue
            
            dist = road_info.iloc[0]["Distance(km)"]
            cap = road_info.iloc[0]["Current Capacity(vehicles/hour)"]
            cond = road_info.iloc[0]["Condition(1-10)"]
            
            # Get population features
            from_pop = neighborhoods_df[neighborhoods_df["ID"] == from_id].iloc[0]["Population"]
            to_pop = neighborhoods_df[neighborhoods_df["ID"] == to_id].iloc[0]["Population"]
            
            for period, col in time_periods.items():
                flow = row[col]
                data.append([from_id, to_id, dist, cap, cond, from_pop, to_pop, time_mapping[period], flow])
        
        df = pd.DataFrame(data, columns=["FromID", "ToID", "Distance", "Capacity", "Condition", "FromPop", "ToPop", "TimePeriod", "Flow"])
        return df

    def train(self, traffic_df, roads_df, neighborhoods_df):
        df = self.prepare_data(traffic_df, roads_df, neighborhoods_df)
        X = df.drop("Flow", axis=1)
        y = df["Flow"]
        
        self.model.fit(X, y)
        self.is_trained = True
        print("Traffic Prediction Model Trained Successfully.")

    def predict(self, from_id, to_id, dist, cap, cond, from_pop, to_pop, time_period_str):
        if not self.is_trained:
            return None
        
        time_mapping = {"morning": 0, "afternoon": 1, "evening": 2, "night": 3}
        time_val = time_mapping.get(time_period_str.lower(), 0)
        
        features = np.array([[from_id, to_id, dist, cap, cond, from_pop, to_pop, time_val]])
        prediction = self.model.predict(features)[0]
        return prediction

def get_predictor(data_files):
    predictor = TrafficPredictor()
    traffic_df = pd.read_excel(data_files["traffic_flow"])
    roads_df = pd.read_excel(data_files["existing_roads"])
    neighborhoods_df = pd.read_excel(data_files["neighborhoods"])
    predictor.train(traffic_df, roads_df, neighborhoods_df)
    return predictor
