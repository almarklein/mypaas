import time

import mypaas.daemon


class SpecialSystemStatsProducer(mypaas.daemon.SystemStatsProducer):
    def __init__(self):
        super().__init__()
        self.data = []

    def _send(self, stat):
        self.data.append(stat)


def test_system_producer():
    producer = SpecialSystemStatsProducer()

    # Run the producer for 1 second
    producer.start()
    time.sleep(1.2)
    producer._stop = True

    data = producer.data
    assert len(data) >= 1
    assert data[0]["group"] == "system"
    assert "cpu|num|%" in data[0]
    assert 0 <= data[0]["cpu|num|%"] <= 100


if __name__ == "__main__":
    test_system_producer()
