import pykka
import traceback
import sys

class AbstractActor(pykka.ThreadingActor):
    def on_receive(self, message):
        try:
            fun_name = message.get("type") + "_message"
            
            if not hasattr(self, fun_name):
                print(f'[ERR] Uknown message type {fun_name}')
                return
            fun = getattr(self, fun_name)

            del message["type"]
            
            return fun(**message)

        except Exception as e:
            print(e)
            traceback.print_exc()
            sys.exit(1)

