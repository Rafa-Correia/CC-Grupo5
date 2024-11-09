import socket
import json
import threading
import os

class AlertFlow:
    def __init__(self):
        self.conditions = {}

    def add_condition(self, condition_name, threshold, operator):
        self.conditions[condition_name] = {"threshold": threshold, "operator": operator}
        print(f"[ALERTFLOW] - [add_condition]: CONDITION '{condition_name}' ADDED WITH THRESHOLD {threshold} AND OPERATOR '{operator}'")

    def evaluate_metrics(self, metrics):
        alerts = {}
        for condition, config in self.conditions.items():
            if condition in metrics:
                metric_value = metrics[condition]
                threshold = config["threshold"]
                operator = config["operator"]

                if operator == ">" and metric_value > threshold:
                    alerts[condition] = f"ALERT: {condition} = {metric_value} exceeds {threshold}"
                elif operator == "<" and metric_value < threshold:
                    alerts[condition] = f"ALERT: {condition} = {metric_value} below {threshold}"

        if alerts:
            print(f"[ALERTFLOW] - [evaluate_metrics]: ALERTS TRIGGERED: {alerts}")
        else:
            print(f"[ALERTFLOW] - [evaluate_metrics]: NO ALERTS TRIGGERED")

        return alerts

if __name__ == "__main__":
    alert_flow = AlertFlow()
    alert_flow.add_condition("cpu_usage", 80, ">")
    alert_flow.add_condition("ram_usage", 90, ">")
    
    sample_metrics = {"cpu_usage": 85, "ram_usage": 70}
    alerts = alert_flow.evaluate_metrics(sample_metrics)