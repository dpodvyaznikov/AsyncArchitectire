import json
from uuid import uuid4

from db.crud import cur_date
from schema_registry import validate
from routing import AccountingPika

if __name__ == "__main__":
    message = {
        "title": "Accounting.DayEnded.v1",
        "properties": {
            "event_id": str(uuid4()),
            "event_version": 1,
            "producer": "accounting.payoff",
            "data": {
                "day": cur_date(),
            }
        }
    }

    validate.validate_event(message, './schema_registry/tracker/task_finished', 'v1.json')
    AccountingPika.send_event(routing_key='task.finished', message=json.dumps(message))
