from absl import app
from absl import flags
from absl import logging

from py.examples.hello_tests.greeter import Greeter

# most of the below was shamelessly stolen from https://abseil.io/docs/python/quickstart

FLAGS = flags.FLAGS
flags.DEFINE_string("name", None, "Your name.")
flags.DEFINE_integer("num_times", 1, "Number of times to print greeting.")

# Required flag.
flags.mark_flag_as_required("name")


def main(argv):
    del argv  # Unused.

    greeter_obj = Greeter(FLAGS.name)

    for i in range(0, FLAGS.num_times):
        logging.info(greeter_obj.Greet())


app.run(main)
