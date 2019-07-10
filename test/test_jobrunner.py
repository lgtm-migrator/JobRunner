# -*- coding: utf-8 -*-
import os
import socket
import unittest
from copy import deepcopy
from unittest.mock import patch

from mock import MagicMock
from nose.plugins.attrib import attr
from requests import ConnectionError

from JobRunner.JobRunner import JobRunner
from test.mock_data import CATALOG_GET_MODULE_VERSION, NJS_JOB_PARAMS, \
    CATALOG_LIST_VOLUME_MOUNTS


class MockLogger(object):
    def __init__(self):
        self.lines = []
        self.errors = []
        self.all = []

    def log_lines(self, lines):
        self.all.extend(lines)

    def log(self, line):
        self.lines.append(line)
        self.all.append([line, 0])

    def error(self, line):
        self.errors.append(line)
        self.all.append([line, 1])


class JobRunnerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = os.environ.get('KB_AUTH_TOKEN', '')
        cls.admin_token = os.environ.get('KB_ADMIN_AUTH_TOKEN', 'bogus')
        cls.cfg = {}
        base = 'https://ci.kbase.us/services/'
        if 'TEST_URL' in os.environ:
            base = "http://%s/services/" % (os.environ['TEST_URL'])
        cls.njs_url = base + 'njs_wrapper'
        cls.jobid = '1234'
        cls.workdir = '/tmp/jr/'
        cls.cfg['token'] = cls.token
        cls.config = {
            'catalog-service-url': base + 'catalog',
            'auth-service-url': base + 'auth/api/legacy/KBase/Sessions/Login',
            'auth2-url': base + 'auth/api/V2/token',
            'workdir': '/tmp/jr'
            }
        if not os.path.exists('/tmp/jr'):
            os.mkdir('/tmp/jr')
        if 'KB_ADMIN_AUTH_TOKEN' not in os.environ:
            os.environ['KB_ADMIN_AUTH_TOKEN'] = 'bogus'

    def _cleanup(self, job):
        d = os.path.join(self.workdir, job)
        if os.path.exists(d):
            for fn in ['config.properties', 'input.json', 'output.json',
                       'token']:
                if os.path.exists(os.path.join(d, fn)):
                    os.unlink(os.path.join(d, fn))
            os.rmdir(d)

    @attr('offline')
    @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    @patch('JobRunner.JobRunner.NJS', autospec=True)
    def test_run_sub(self, mock_njs, mock_auth):
        self._cleanup(self.jobid)
        params = deepcopy(NJS_JOB_PARAMS)
        params[0]['method'] = 'RunTester.run_RunTester'
        params[0]['params'] = [{'depth': 3, 'size': 1000, 'parallel': 5}]
        params[1]['auth-service-url'] = self.config['auth-service-url']
        params[1]['auth.service.url.v2'] = self.config['auth2-url']
        jr = JobRunner(self.config, self.njs_url, self.jobid, self.token,
                       self.admin_token)
        rv = deepcopy(CATALOG_GET_MODULE_VERSION)
        rv['docker_img_name'] = 'test/runtester:latest'
        jr.cc.catalog.get_module_version = MagicMock(return_value=rv)
        jr.cc.catalog.list_volume_mounts = MagicMock(return_value=[])
        jr.cc.catalog.get_secure_config_params = MagicMock(return_value=None)
        jr.logger.njs.add_job_logs = MagicMock(return_value=rv)
        jr.njs.get_job_params.return_value = params
        jr.njs.check_job_canceled.return_value = {'finished': False}
        jr.auth.get_user.return_value = "bogus"
        out = jr.run()
        self.assertIn('result', out)
        self.assertNotIn('error', out)

    @attr('offline')
    @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    @patch('JobRunner.JobRunner.NJS', autospec=True)
    def test_run(self, mock_njs, mock_auth):
        self._cleanup(self.jobid)
        params = deepcopy(NJS_JOB_PARAMS)
        params[0]['method'] = 'mock_app.bogus'
        params[0]['params'] = {'param1': 'value1'}
        jr = JobRunner(self.config, self.njs_url, self.jobid, self.token,
                       self.admin_token)
        rv = deepcopy(CATALOG_GET_MODULE_VERSION)
        rv['docker_img_name'] = 'mock_app:latest'
        # jr.mr.catalog.get_module_version = MagicMock(return_value=rv)
        # jr.mr.catalog.list_volume_mounts = MagicMock(return_value=[])
        jr.cc.catalog.get_module_version = MagicMock(return_value=rv)
        jr.cc.catalog.list_volume_mounts = MagicMock(return_value=[])
        jr.cc.catalog.get_secure_config_params = MagicMock(return_value=None)
        jr.logger.njs.add_job_logs = MagicMock(return_value=rv)
        jr.njs.get_job_params.return_value = params
        jr.njs.check_job_canceled.return_value = {'finished': False}
        jr.auth.get_user.return_value = "bogus"
        out = jr.run()
        self.assertIn('result', out)
        self.assertNotIn('error', out)

    @attr('offline')
    @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    @patch('JobRunner.JobRunner.NJS', autospec=True)
    def test_run_volume(self, mock_njs, mock_auth):
        self._cleanup(self.jobid)
        params = deepcopy(NJS_JOB_PARAMS)
        params[0]['method'] = 'mock_app.voltest'
        params[0]['params'] = {'param1': 'value1'}
        jr = JobRunner(self.config, self.njs_url, self.jobid, self.token,
                       self.admin_token)
        rv = deepcopy(CATALOG_GET_MODULE_VERSION)
        rv['docker_img_name'] = 'mock_app:latest'
        vols = deepcopy(CATALOG_LIST_VOLUME_MOUNTS)
        jr.cc.catalog.get_module_version = MagicMock(return_value=rv)
        jr.cc.catalog.list_volume_mounts = MagicMock(return_value=vols)
        jr.cc.catalog.get_secure_config_params = MagicMock(return_value=None)
        jr.logger.njs.add_job_logs = MagicMock(return_value=rv)
        jr.njs.get_job_params.return_value = params
        jr.njs.check_job_canceled.return_value = {'finished': False}
        jr.auth.get_user.return_value = "bogus"
        if not os.path.exists('/tmp/bogus'):
            os.mkdir('/tmp/bogus')
        with open('/tmp/bogus/input.fa', 'w') as f:
            f.write('>contig-50_0 length_64486 read_count_327041\n')
            f.write('GTCGTGCTGCTGCCGATCGACCGCGCCTATGCGATGTTGCCGGACGGCATCC\n')
        out = jr.run()
        self.assertIn('result', out)
        self.assertNotIn('error', out)

    @attr('offline')
    @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    @patch('JobRunner.JobRunner.NJS', autospec=True)
    def test_cancel(self, mock_njs, mock_auth):
        self._cleanup(self.jobid)
        params = deepcopy(NJS_JOB_PARAMS)
        params[0]['method'] = 'RunTester.run_RunTester'
        params[0]['params'] = [{'depth': 3, 'size': 1000, 'parallel': 4}]
        jr = JobRunner(self.config, self.njs_url, self.jobid, self.token,
                       self.admin_token)
        rv = deepcopy(CATALOG_GET_MODULE_VERSION)
        rv['docker_img_name'] = 'test/runtester:latest'
        jr.cc.catalog.get_module_version = MagicMock(return_value=rv)
        jr.cc.catalog.list_volume_mounts = MagicMock(return_value=[])
        jr.cc.catalog.get_secure_config_params = MagicMock(return_value=None)
        jr.logger.njs.add_job_logs = MagicMock(return_value=rv)
        jr.njs.get_job_params.return_value = params
        nf = {'finished': False}
        jr.njs.check_job_canceled.side_effect = [nf, nf, nf, nf, nf,
                                                 {'finished': True}]
        jr.auth.get_user.return_value = "bogus"
        out = jr.run()
        self.assertIsNotNone(out)
        # Check that all containers are gone

    @attr('offline')
    @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    @patch('JobRunner.JobRunner.NJS', autospec=True)
    def test_max_jobs(self, mock_njs, mock_auth):
        self._cleanup(self.jobid)
        params = deepcopy(NJS_JOB_PARAMS)
        params[0]['method'] = 'RunTester.run_RunTester'
        params[0]['params'] = [{'depth': 2, 'size': 1000, 'parallel': 5}]
        config = deepcopy(self.config)
        config['max_tasks'] = 2
        jr = JobRunner(config, self.njs_url, self.jobid, self.token,
                       self.admin_token)
        rv = deepcopy(CATALOG_GET_MODULE_VERSION)
        rv['docker_img_name'] = 'test/runtester:latest'
        jr.cc.catalog.get_module_version = MagicMock(return_value=rv)
        jr.cc.catalog.list_volume_mounts = MagicMock(return_value=[])
        jr.cc.catalog.get_secure_config_params = MagicMock(return_value=None)
        jr.logger.njs.add_job_logs = MagicMock(return_value=rv)
        jr.njs.get_job_params.return_value = params
        jr.njs.check_job_canceled.return_value = {'finished': False}
        jr.auth.get_user.return_value = "bogus"
        out = jr.run()
        self.assertIn('error', out)
        # Check that all containers are gone

    @attr('online')
    @patch('JobRunner.JobRunner.NJS', autospec=True)
    def test_run_online(self, mock_njs):
        self._cleanup(self.jobid)
        params = deepcopy(NJS_JOB_PARAMS)
        jr = JobRunner(self.config, self.njs_url, self.jobid, self.token,
                       self.admin_token)
        rv = deepcopy(CATALOG_GET_MODULE_VERSION)
        rv['docker_img_name'] = 'mock_app:latest'
        jr.logger.njs.add_job_logs = MagicMock(return_value=rv)
        jr.njs.check_job_canceled.return_value = {'finished': False}
        jr.njs.get_job_params.return_value = params
        out = jr.run()
        self.assertIn('result', out)
        self.assertNotIn('error', out)

    @patch('JobRunner.JobRunner.NJS', autospec=True)
    @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    def test_token(self, mock_njs, mock_auth):
        self._cleanup(self.jobid)
        params = deepcopy(NJS_JOB_PARAMS)
        os.environ['KB_AUTH_TOKEN'] = 'bogus'
        jr = JobRunner(self.config, self.njs_url, self.jobid, self.token,
                       self.admin_token)
        jr.njs.check_job_canceled.return_value = {'finished': False}
        jr.njs.get_job_params.return_value = params
        jr.auth.get_user.side_effect = OSError()
        with self.assertRaises(Exception):
            jr.run()

    @patch('JobRunner.JobRunner.NJS', autospec=True)
    @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    def test_canceled_job(self, mock_njs, mock_auth):
        self._cleanup(self.jobid)
        mlog = MockLogger()
        params = deepcopy(NJS_JOB_PARAMS)
        os.environ['KB_AUTH_TOKEN'] = 'bogus'
        jr = JobRunner(self.config, self.njs_url, self.jobid, self.token,
                       self.admin_token)
        jr.logger = mlog
        jr.njs.check_job_canceled.return_value = {'finished': True}
        with self.assertRaises(OSError):
            jr.run()
        self.assertEquals(mlog.errors[0], 'Job already run or canceled')

    @patch('JobRunner.JobRunner.NJS', autospec=True)
    @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    def test_error_update(self, mock_njs, mock_auth):
        self._cleanup(self.jobid)
        mlog = MockLogger()
        params = deepcopy(NJS_JOB_PARAMS)
        os.environ['KB_AUTH_TOKEN'] = 'bogus'
        jr = JobRunner(self.config, self.njs_url, self.jobid, self.token,
                       self.admin_token)
        jr.logger = mlog
        jr.njs.check_job_canceled.return_value = {'finished': False}
        jr.njs.update_job.side_effect = ConnectionError()
        jr.njs.get_job_params.side_effect = ConnectionError()
        with self.assertRaises(ConnectionError):
            jr.run()
        self.assertEquals(mlog.errors[0], 'Failed to get job parameters. Exiting.')

    @patch('JobRunner.JobRunner.NJS', autospec=True)
    @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    def test_config(self, mock_njs, mock_auth):
        self._cleanup(self.jobid)
        params = deepcopy(NJS_JOB_PARAMS)
        os.environ['KB_AUTH_TOKEN'] = 'bogus'
        jr = JobRunner(self.config, self.njs_url, self.jobid, self.token,
                       self.admin_token)

        config = jr._init_config(self.config, self.jobid, self.njs_url)
        test_config = {'catalog-service-url': 'https://ci.kbase.us/services/catalog',
                       'auth-service-url': 'https://ci.kbase.us/services/auth/api/legacy/KBase/Sessions/Login',
                       'auth2-url': 'https://ci.kbase.us/services/auth/api/V2/token',
                       'workdir': '/tmp/jr', 'hostname': socket.gethostname(),
                       'job_id': self.jobid, 'njs_url': self.njs_url,
                       'token': self.token, 'admin_token': self.admin_token}

        del config['cgroup']

        self.assertEquals(test_config, config)


    @patch('JobRunner.JobRunner.NJS', autospec=True)
    @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    def test_job_ready_to_run(self, mock_njs, mock_auth):
        self._cleanup(self.jobid)
        params = deepcopy(NJS_JOB_PARAMS)
        os.environ['KB_AUTH_TOKEN'] = 'bogus'
        jr = JobRunner(self.config, self.njs_url, self.jobid, self.token,
                       self.admin_token)

        jr.njs.check_job_canceled.return_value = {'finished': False}
        ready_to_run = jr._job_ready_to_run()
        self.assertEquals(ready_to_run, True)
    
        jr.njs.check_job_canceled.return_value = {'finished': True}
        ready_to_run = jr._job_ready_to_run()
        self.assertEquals(ready_to_run, False)
