import eventlet

from kombu import Connection
from kombu.mixins import ConsumerMixin

from st2common.constants.action import LIVEACTION_COMPLETED_STATES
from st2common import log as logging
from st2common.models.api.execution import ActionExecutionAPI
from st2common.transport import execution, publishers
from st2common.transport import utils as transport_utils

__all__ = [
    'get_listener',
    'get_listener_if_set'
]

LOG = logging.getLogger(__name__)

_listener = None


class Listener(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection
        self.listeners = []

    def get_consumers(self, consumer, channel):
        queue = execution.get_queue(routing_key=publishers.ANY_RK,
                                    exclusive=True)
        return [
            consumer(queues=[queue],
                     accept=['pickle'],
                     callbacks=[self.processor])
        ]

    def processor(self, body, message):
        try:
            body = ActionExecutionAPI.from_model(body)

            for listener in self.listeners:
                if listener['id'] == body.id and body.status in LIVEACTION_COMPLETED_STATES:
                    listener['event'].send(body)
                    self.listeners.remove(listener)
        finally:
            message.ack()

    def listen(self, id, event):
        self.listeners.append({
            'id': id,
            'event': event
        })


def listen(listener):
    try:
        listener.run()
    finally:
        listener.shutdown()


def get_listener():
    global _listener
    if not _listener:
        with Connection(transport_utils.get_messaging_urls()) as conn:
            _listener = Listener(conn)
            eventlet.spawn_n(listen, _listener)
    return _listener


def get_listener_if_set():
    global _listener
    return _listener
