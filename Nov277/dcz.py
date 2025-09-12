import multiprocessing
from queue import Queue
import time
import random


class DataStreamProcessor:
    def __init__(self, num_workers=4):
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.num_workers = num_workers

    def data_generator(self, total_records=1000):
        for _ in range(total_records):
            # Simulate streaming data
            record = {
                'timestamp': time.time(),
                'value': random.uniform(0, 100),
                'category': random.choice(['A', 'B', 'C'])
            }
            self.input_queue.put(record)
            time.sleep(0.01)  # Simulate stream delay

    def process_data(self):
        while not self.input_queue.empty():
            record = self.input_queue.get()
            # Perform real-time processing
            processed_record = {
                'timestamp': record['timestamp'],
                'normalized_value': (record['value'] - 50) / 25,
                'category': record['category']
            }
            self.output_queue.put(processed_record)

    def start_processing(self):
        # Create worker processes
        workers = [
            multiprocessing.Process(target=self.process_data)
            for _ in range(self.num_workers)
        ]

        # Start data generation and worker processes
        generator = multiprocessing.Process(target=self.data_generator)
        generator.start()

        for worker in workers:
            worker.start()

        generator.join()
        for worker in workers:
            worker.join()
