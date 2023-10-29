from enum import Enum

class DatabaseOperationTypes(Enum):
    ADD_CONTACTED_LEADS = 1
    ADD_SETUP = 2
    GET_CONTACTED_LEADS = 3
    GET_SETUP = 4
    REMOVE_CONTACTED_LEADS = 5
    REMOVE_SETUP = 6
    UPDATE_CONTACTED_LEADS = 7
    UPDATE_SETUP = 8