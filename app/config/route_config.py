AUTH_LOGIN = '/auth/login'
AUTH_REGISTER = '/auth/register'
AUTH_LOGOUT = '/auth/logout'
AUTH_FORGOT_PASSWORD = '/auth/forgot-password'


MACHINES_PUMPS = '/machines/pumps'
MACHINES_PARTS = '/machines/parts'
MACHINES_CREATE_PUMP = '/machines/pumps/create'
MACHINES_CREATE_PART = '/machines/parts/create'
MACHINE_DETAILS = '/machines/details/{id}'
MACHINE_SERVICE_REPORTS = '/machines/{id}/service-reports'
MACHINE_DELETE = '/machines/{id}/delete'
MACHINE_UPDATE = '/machines/{id}/update'


USERS_ADMINS = '/users/admins'
USERS_DISTRIBUTERS = '/users/distributers'
USER_DELETE = '/users/{id}/delete'


SERVICE_REPORTS = '/service-reports'
SERVICE_REPORTS_TYPES = '/service-reports/types'
SERVICE_REPORTS_MACHINE = '/service-reports/machine/{serial_no}'
SERVICE_REPORT_CUSTOMER = '/service-reports/customer'


DASHBOARD_STATS = '/dashboard/stats'
DASHBOARD_RECENT_ACTIVITIES = '/dashboard/recent-activities'
DASHBOARD_SERVICE_REPORT = '/dashboard/service-report/{report_id}'