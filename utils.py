import logging

#Logging configuration
log = logging.getLogger('autosub')

def str_to_bool(s):
    #Converts a string to a boolean value
    if s == 'True' or 'true':
         return True
    elif s == 'False' or 'false':
         return False
    else:
        log.error(f'Invalid boolean value: {s}')