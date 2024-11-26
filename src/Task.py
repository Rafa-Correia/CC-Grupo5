from DataBlocks import *
import json

class PerDeviceTask: #note, while a task may have many devices, this class contains all info pertaining to a single device's task
    def __init__(self, task_id = 0, device_id = "ERR", cpu_inf = {}, ram_inf = {}, interface_inf = {}, bandwidth_inf = {}, jitter_inf = {}, loss_inf = {}, latency_inf = {}):
        self.task_id = task_id
        self.device_id = device_id
        self.cpu_inf = cpu_inf
        self.ram_inf = ram_inf
        self.interface_inf = interface_inf
        self.bandwidth_inf = bandwidth_inf
        self.jitter_inf = jitter_inf
        self.loss_inf = loss_inf
        self.latency_inf = latency_inf

    def to_blocks(self):
        blocks = []
        
        #==============================================================
        #                             CPU
        #==============================================================
        cpu_active = self.cpu_inf.get("active", False)
        if cpu_active:
            cpu_freq = self.cpu_inf.get("frequency", 0)
            cpu_duration = self.cpu_inf.get("duration", 0)
            cpu_alert = self.cpu_inf.get("alert_con", 0)
            cpu_block = DataBlockServer(id=CPU, frequency=cpu_freq, max_value=cpu_alert, duration=cpu_duration)
            #print(f"Task {self.task_id} of device {self.device_id} has block of type CPU with following values: {cpu_freq}, {cpu_duration}, {cpu_alert}")
            blocks.append(cpu_block)

        #==============================================================
        #                             RAM
        #==============================================================
        ram_active = self.ram_inf.get("active", False)
        if ram_active:
            ram_freq = self.ram_inf.get("frequency", 0)
            ram_alert = self.ram_inf.get("alert_con", 0)
            ram_block = DataBlockServer(id=RAM, frequency=ram_freq, max_value=ram_alert)
            #print(f"Task {self.task_id} of device {self.device_id} has block of type RAM with following values: {ram_freq}, {ram_alert}")
            blocks.append(ram_block)

        #==============================================================
        #                          INTERFACE
        #==============================================================
        interface_active = self.interface_inf.get("active", False)
        if interface_active:
            interface_freq = self.interface_inf.get("frequency", 0)
            interface_alert = self.interface_inf.get("alert_con", 0)
            interface_block = DataBlockServer(id=INTERFACE, frequency=interface_freq, max_value=interface_alert)
            blocks.append(interface_block)

        #==============================================================
        #                          BANDWIDTH
        #==============================================================
        bandwidth_active = self.bandwidth_inf.get("active", False)
        if bandwidth_active:
            bandwidth_freq = self.bandwidth_inf.get("frequency", 0)
            bandwidth_client = self.bandwidth_inf.get("is_client", False)
            bandwidth_duration = self.bandwidth_inf.get("duration", 0)
            bandwidth_s_ip = self.bandwidth_inf.get("source_ip", "0.0.0.0")
            bandwidth_d_ip = self.bandwidth_inf.get("destination_ip", "0.0.0.0")
            bandwidth_block = DataBlockServer(id=BANDWIDTH, frequency=bandwidth_freq, client_mode=bandwidth_client, duration=bandwidth_duration, source_ip=bandwidth_s_ip, destination_ip=bandwidth_d_ip)
            blocks.append(bandwidth_block)

        #==============================================================
        #                           JITTER
        #==============================================================
        jitter_active = self.jitter_inf.get("active", False)
        if jitter_active:
            jitter_freq = self.jitter_inf.get("frequency", 0)
            jitter_alert = self.jitter_inf.get("alert_con", 0)
            jitter_client = self.jitter_inf.get("is_client", False)
            jitter_duration = self.jitter_inf.get("duration", 0)
            jitter_s_ip = self.jitter_inf.get("source_ip", "0.0.0.0")
            jitter_d_ip = self.jitter_inf.get("destination_ip", "0.0.0.0")
            jitter_block = DataBlockServer(id=JITTER, frequency=jitter_freq, max_value=jitter_alert, client_mode=jitter_client, duration=jitter_duration, source_ip=jitter_s_ip, destination_ip=jitter_d_ip)
            blocks.append(jitter_block)

        #==============================================================
        #                            LOSS
        #==============================================================
        loss_active = self.loss_inf.get("active", False)
        if loss_active:
            loss_freq = self.loss_inf.get("frequency", 0)
            loss_alert = self.loss_inf.get("alert_con", 0)
            loss_client = self.loss_inf.get("is_client", False)
            loss_duration = self.loss_inf.get("duration", 0)
            loss_s_ip = self.loss_inf.get("source_ip", "0.0.0.0")
            loss_d_ip = self.loss_inf.get("destination_ip", "0.0.0.0")
            loss_block = DataBlockServer(id=LOSS, frequency=loss_freq, max_value=loss_alert, client_mode=loss_client, duration=loss_duration, source_ip=loss_s_ip, destination_ip=loss_d_ip)
            blocks.append(loss_block)

        #==============================================================
        #                          LATENCY
        #==============================================================
        latency_active = self.latency_inf.get("active", False)
        if latency_active:
            latency_freq = self.latency_inf.get("frequency", 0)
            latency_duration = self.latency_inf.get("duration", 0)
            latency_s_ip = self.latency_inf.get("source_ip", "0.0.0.0")
            latency_d_ip = self.latency_inf.get("destination_ip", "0.0.0.0")
            latency_block = DataBlockServer(id=LATENCY, frequency=latency_freq, duration=latency_duration, source_ip=latency_s_ip, destination_ip=latency_d_ip)
            blocks.append(latency_block)

        #print(f"  [TASK] RETURNING {blocks}")
        return blocks

    def to_bytes(self):
        blocks = self.to_blocks()
        block_stream = b''
        for block in blocks:
            packed_block = block.to_bytes()
            if packed_block is None:
                print("UH OH 2 why")
            block_stream += packed_block
        
        return block_stream


class TaskInterpreter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.devices_with_tasks = {}

    def load_tasks(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                tasks = data.get('tasks', [])
                print("[NMS_SERVER] - [load_tasks]: PARSING TASKS...\n")
                for task in tasks:
                    task_id = task.get("task_id", "UNKNOWN")
                    devices = task.get("devices", [])
                    print(f"[NMS_SERVER] - [load_tasks]: TASK ID: {task_id}")
                    for device in devices:
                        device_id = device.get("device_id", "UNKNOWN")
                        self.devices_with_tasks[device_id] = []

                        device_metrics = device.get("device_metrics", {})
                        link_metrics = device.get("link_metrics", {})

                        cpu_inf = device_metrics.get("cpu", {})
                        ram_inf = device_metrics.get("ram", {})
                        interface_inf = device_metrics.get("interface", {})

                        bandwidth_inf = link_metrics.get("bandwidth", {})
                        jitter_inf = link_metrics.get("jitter", {})
                        loss_inf = link_metrics.get("loss", {})
                        latency_inf = link_metrics.get("latency", {})

                        print(f"  [NMS_SERVER] - DEVICE ID: {device_id}")
                        print("    METRICS:")
                        print(f"      CPU: {cpu_inf}")
                        print(f"      RAM: {ram_inf}")
                        print(f"      INTERFACE: {interface_inf}")
                        print(f"      BANDWIDTH: {bandwidth_inf}")
                        print(f"      JITTER: {jitter_inf}")
                        print(f"      LOSS: {loss_inf}")
                        print(f"      LATENCY: {latency_inf}")

                        print("\n")

                        t = PerDeviceTask(task_id, device_id,cpu_inf, ram_inf, interface_inf, bandwidth_inf, jitter_inf, loss_inf, latency_inf)
                        self.devices_with_tasks[device_id].append(t)

                print("[NMS_SERVER] - [load_tasks]: TASKS LOADED SUCCESSFULLY.")
        except FileNotFoundError:
            print(f"[NMS_SERVER] - [load_tasks]: FILE NOT FOUND: {self.file_path}")
        except json.JSONDecodeError:
            print("[NMS_SERVER] - [load_tasks]: FAILED TO DECODE THE JSON FILE. CHECK THE FORMAT.")

    def assign_task_to_agent(self, agent_address):
        if not self.devices:
            print(f"[NMS_SERVER] - [assign_task_to_agent]: NO TASKS AVAILABLE TO ASSIGN TO {agent_address}")
            return "NO TASKS AVAILABLE"

        task = self.devices.pop(0)
        task_info = f"TASK ASSIGNED: {task.get('device_id')}"
        print(f"[NMS_SERVER] - [assign_task_to_agent]: {task_info} TO AGENT {agent_address}")
        return json.dumps(task)
