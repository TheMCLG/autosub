import logging

# Logging configuration
log = logging.getLogger("autosub")


def str_to_bool(s):
    # Converts a string to a boolean value
    if s == "True" or s == "true":
        return True
    elif s == "False" or s == "false":
        return False
    else:
        log.error(f"Invalid boolean value: {s}")


def str_to_list(s):
    # Converts a string to a list
    if s == "None":
        return None
    if s:
        if " " in s and not ", " in s:
            log.error(f"Inconsistent list formatting: {s}")
        elif ", " in s:
            return s.split(", ")
        elif "," in s:
            return s.split(",")
        elif not ", " in s and not "," in s:
            s = [s]
            return s
        else:
            log.error(f"Invalid list value: {s}")
