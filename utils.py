import logging

#Logging configuration
log = logging.getLogger('autosub')

def str_to_bool(s):
    #Converts a string to a boolean value
    if s == 'True' or s == 'true':
         return True
    elif s == 'False' or s == 'false':
         return False
    else:
        log.error(f'Invalid boolean value: {s}')