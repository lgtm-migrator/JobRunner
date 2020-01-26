#!/usr/bin/env python

import logging
import os
import sys

from docker.models.containers import Container

from JobRunner.JobRunner import JobRunner

logging.basicConfig(level=logging.INFO)
_TOKEN_ENV = "KB_AUTH_TOKEN"
_ADMIN_TOKEN_ENV = "KB_ADMIN_AUTH_TOKEN"
_DEBUG = "DEBUG_MODE"


def _get_debug_mode():
    """
    Check to see if this job run is in debug mode
    :return:
    """
    if _DEBUG in os.environ:
        if os.environ[_DEBUG].lower() == 'true':
            return True
    return False

def _get_token():
    # Get the token from the environment or a file.
    # Set the KB_AUTH_TOKEN if not set.
    if _TOKEN_ENV in os.environ:
        token = os.environ[_TOKEN_ENV]
    else:
        try:
            with open('token') as f:
                token = f.read().rstrip()
            os.environ[_TOKEN_ENV] = token
        except:
            print("Failed to get token.")
            sys.exit(2)
    return token


def _get_admin_token():
    if _ADMIN_TOKEN_ENV not in os.environ:
        print("Missing admin token needed for volume mounts.")
        sys.exit(2)
    admin_token = os.environ.pop('KB_ADMIN_AUTH_TOKEN')
    if _ADMIN_TOKEN_ENV in os.environ:
        print("Failed to sanitize environment")
    return admin_token


def terminate_job(jr: JobRunner):
    """
    Unexpected Job Error, so attempt to finish the job, and if that fails, attempt to cancel the job
    """
    params = {'job_id': jr.job_id,
              'error_message': 'Unexpected Job Error',
              'error_code': 2,
              'terminated_code': 2
              }

    try:
        jr.ee2.finish_job(params=params)
    except Exception:
        try:
            jr.ee2.cancel_job(params=params)
        except Exception:
            pass

    # Attempt to clean up Docker and Special Runner Containers
    # Kill Callback Server
    jr.mr.cleanup_all(debug=_get_debug_mode())
    jr.cbs.kill()


def main():
    # Input job id and njs_service URL
    if len(sys.argv) == 3:
        job_id = sys.argv[1]
        ee2_url = sys.argv[2]
    else:
        print("Incorrect usage")
        sys.exit(1)

    config = dict()
    config['workdir'] = os.getcwd()
    if not os.path.exists(config['workdir']):
        os.makedirs(config['workdir'])
        logging.info(f"Creating work directory at {config['workdir']}")

    config['catalog-service-url'] = ee2_url.replace('ee2', 'catalog')
    auth_ext = 'auth/api/legacy/KBase/Sessions/Login'
    config['auth-service-url'] = ee2_url.replace('ee2', auth_ext)

    # WARNING: Condor job environment may not inherit from system ENV
    if 'USE_SHIFTER' in os.environ:
        config['runtime'] = 'shifter'

    if 'JR_MAX_TASKS' in os.environ:
        config['max_tasks'] = int(os.environ['JR_MAX_TASKS'])

    token = _get_token()
    at = _get_admin_token()
    debug = _get_debug_mode()


    try:
        logging.info("About to create job runner")

        jr = JobRunner(config, ee2_url, job_id, token, at, debug)
        logging.info(f'Debug Mode is {debug}')
        jr.logger.info(f'Debug Mode is {debug}')
        logging.info("About to run job")
        jr.run()
    except Exception as e:
        logging.error("An unhandled error was encountered")
        logging.error(e)
        terminate_job(jr)
        sys.exit(2)


if __name__ == '__main__':
    main()
