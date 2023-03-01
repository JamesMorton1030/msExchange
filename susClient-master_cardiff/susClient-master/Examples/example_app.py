from apps import BaseApp, BaseTask


class ExampleTask(BaseTask):

    def start(self): # Optional
        print("ExampleTask starting")
        self.count = 5

    def stop(self): # Optional
        print("ExampleTask ending")

    def switch_in(self): # Optional
        print("ExampleTask switching in")

    def switch_out(self): # Optional
        print("ExampleTask switching out")

    def main(self): # Required
        while self.count > 0:
            self.count -= 1
            print("ExampleTask Running")
            yield # yield is required in this method


class AnotherTask(BaseTask):

    def start(self): # Optional
        print("AnotherTask starting")
        self.count = 2

    def stop(self): # Optional
        print("AnotherTask ending")

    def switch_in(self): # Optional
        print("AnotherTask switching in")

    def switch_out(self): # Optional
        print("AnotherTask switching out")

    def main(self): # Required
        while self.count > 0:
            self.count -= 1
            print("AnotherTask Running")
            yield # yield is required in this method


class ExampleApp(BaseApp):

    TASKS = {"Example": ExampleTask, "Another": AnotherTask}

    def open(self): # Optional
        print("Starting application")
        return "Application"

    def close(self): # Optional
        print("Closing application")


def setup(client):
    client.add_app(ExampleApp)