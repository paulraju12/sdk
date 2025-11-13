from enum import Enum

class Action(Enum):
    LIST_SERVICES = "list_services"
    LIST_INTEGRATIONS = "list_integrations"
    LIST_ORGANIZATIONS = "list_organizations"
    LIST_COLLECTIONS = "list_collections"
    CONFIRM_TICKET_CREATION = "confirm_ticket_creation"
    CREATE_TICKET = "create_ticket"
    LIST_TICKETS = "list_tickets"
    HEALTH_CHECK = "health_check"