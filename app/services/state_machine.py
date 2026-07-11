from app.config.enums import PaymentStatus

# Maps each status to the set of statuses it is allowed to transition to.
# if any status is mapped to an empty set , then it is a terminal(final) state.
TRANSITIONS : dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.CREATED: {PaymentStatus.AUTHORIZED, PaymentStatus.FAILED},
    PaymentStatus.AUTHORIZED: {PaymentStatus.CAPTURED, PaymentStatus.FAILED},
    PaymentStatus.CAPTURED: {PaymentStatus.SETTLED, PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED},
    PaymentStatus.SETTLED: {PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED},
    PaymentStatus.PARTIALLY_REFUNDED:{PaymentStatus.REFUNDED},
    PaymentStatus.REFUNDED: set(),
    PaymentStatus.FAILED: set(),

}

class InvalidTransitionError(Exception):
    '''Raised when the payment tries to move to a status it is not allowed to move to /reach'''
    pass

def can_transition(current_status: PaymentStatus, target_status: PaymentStatus) -> bool:
    '''Returns True if the transition from current_status to target_status is allowed, False otherwise.
    It doesnot change anything , just true/false'''
    allowed_next_statuses = TRANSITIONS.get(current_status, set())
    return target_status in allowed_next_statuses

def transition(current_status: PaymentStatus, target_status: PaymentStatus) -> PaymentStatus:
    '''Attempt to move the payment to the target status.
       Returns the new status if the transition is allowed, raises InvalidTransitionError otherwise.'''
    if can_transition(current_status, target_status):
        return target_status
    else:
        raise InvalidTransitionError(f"Cannot transition payment from '{current_status.value}' to '{target_status.value}'")
