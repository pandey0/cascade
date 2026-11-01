| scenario | requests | outcome mix | extra |
|---|---|---|---|
| flaky30_failopen | 300 | {'cheap': 277, 'cheap_degraded': 7, 'teacher': 16} | {'healthz_after': 200, 'status_after': 200} |
| flaky30_failclosed | 300 | {'cheap': 277, 'http_503': 5, 'teacher': 18} | {'healthz_after': 200, 'status_after': 200} |
| outage100_failopen | 300 | {'cheap': 277, 'cheap_degraded': 23} | {'healthz_after': 200, 'status_after': 200} |
| slow_teacher_timeout | 300 | {'cheap': 277, 'http_503': 23} | {'healthz_after': 200, 'status_after': 200} |
| sigterm_under_load | 600 | {'cheap': 83, 'teacher': 9, 'conn_ConnectError': 507, 'conn_RemoteProtocolError': 1} | {'requests_before_sigterm': 83, 'exit_code': -15, 'shutdown_s': 0.7} |
