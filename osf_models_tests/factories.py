# -*- coding: utf-8 -*-
import functools
import mock
from mock import patch, Mock

import factory
import pytz
from factory.django import DjangoModelFactory
from django.utils import timezone
from faker import Factory
from modularodm.exceptions import NoResultsFound

from website.util import permissions
from website.project.licenses import ensure_licenses
from website.project.model import ensure_schemas
from website.archiver import ARCHIVER_SUCCESS
from framework.auth.core import Auth

from osf_models import models
from osf_models.models.sanctions import Sanction
from osf_models.utils.names import impute_names_model
from osf_models.modm_compat import Q

fake = Factory.create()
ensure_licenses = functools.partial(ensure_licenses, warn=False)

def get_default_metaschema():
    """This needs to be a method so it gets called after the test database is set up"""
    try:
        return models.MetaSchema.find()[0]
    except IndexError:
        ensure_schemas()
        return models.MetaSchema.find()[0]

def FakeList(provider, n, *args, **kwargs):
    func = getattr(fake, provider)
    return [func(*args, **kwargs) for _ in range(n)]

class UserFactory(DjangoModelFactory):
    fullname = factory.Faker('name')
    username = factory.Faker('email')
    password = factory.PostGenerationMethodCall('set_password',
                                                'queenfan86')
    is_registered = True
    is_claimed = True
    date_confirmed = factory.Faker('date_time_this_decade', tzinfo=pytz.utc)
    merged_by = None
    verification_key = None

    class Meta:
        model = models.OSFUser

    @factory.post_generation
    def set_names(self, create, extracted):
        parsed = impute_names_model(self.fullname)
        for key, value in parsed.items():
            setattr(self, key, value)
        if create:
            self.save()

    @factory.post_generation
    def set_emails(self, create, extracted):
        if self.username not in self.emails:
            self.emails.append(str(self.username))

class UnregUserFactory(DjangoModelFactory):
    email = factory.Faker('email')
    fullname = factory.Faker('name')
    date_confirmed = factory.Faker('date_time', tzinfo=pytz.utc)
    date_registered = factory.Faker('date_time', tzinfo=pytz.utc)

    class Meta:
        model = models.OSFUser

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        '''Build an object without saving it.'''
        ret = target_class.create_unregistered(email=kwargs.pop('email'), fullname=kwargs.pop('fullname'))
        for key, val in kwargs.items():
            setattr(ret, key, val)
        return ret

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        ret = target_class.create_unregistered(email=kwargs.pop('email'), fullname=kwargs.pop('fullname'))
        for key, val in kwargs.items():
            setattr(ret, key, val)
        ret.save()
        return ret


class UnconfirmedUserFactory(DjangoModelFactory):
    """Factory for a user that has not yet confirmed their primary email
    address (username).
    """
    class Meta:
        model = models.OSFUser
    username = factory.Faker('email')
    fullname = factory.Faker('name')
    password = 'lolomglgt'

    @classmethod
    def _build(cls, target_class, username, password, fullname):
        '''Build an object without saving it.'''
        instance = target_class.create_unconfirmed(
            username=username, password=password, fullname=fullname
        )
        instance.date_registered = fake.date_time(tzinfo=pytz.utc)
        return instance

    @classmethod
    def _create(cls, target_class, username, password, fullname):
        instance = target_class.create_unconfirmed(
            username=username, password=password, fullname=fullname
        )
        instance.date_registered = fake.date_time(tzinfo=pytz.utc)

        instance.save()
        return instance


class AbstractNodeFactory(DjangoModelFactory):
    title = factory.Faker('catch_phrase')
    description = factory.Faker('sentence')
    date_created = factory.LazyFunction(timezone.now)
    creator = factory.SubFactory(UserFactory)

    class Meta:
        model = models.Node


class ProjectFactory(AbstractNodeFactory):
    category = 'project'


class NodeFactory(AbstractNodeFactory):
    category = 'hypothesis'
    parent = factory.SubFactory(ProjectFactory)


class InstitutionFactory(DjangoModelFactory):
    name = factory.Faker('company')
    auth_url = factory.Faker('url')
    logout_url = factory.Faker('url')
    domains = FakeList('url', n=3)
    email_domains = FakeList('domain_name', n=1)
    logo_name = factory.Faker('file_name')

    class Meta:
        model = models.Institution

class NodeLicenseRecordFactory(DjangoModelFactory):
    year = factory.Faker('year')
    copyright_holders = FakeList('name', n=3)

    class Meta:
        model = models.NodeLicenseRecord

    @classmethod
    def _create(cls, *args, **kwargs):
        try:
            models.NodeLicense.find_one(
                Q('name', 'eq', 'No license')
            )
        except NoResultsFound:
            ensure_licenses()
        kwargs['node_license'] = kwargs.get(
            'node_license',
            models.NodeLicense.find_one(
                Q('name', 'eq', 'No license')
            )
        )
        return super(NodeLicenseRecordFactory, cls)._create(*args, **kwargs)

class PrivateLinkFactory(DjangoModelFactory):
    class Meta:
        model = models.PrivateLink

    name = factory.Faker('word')
    key = factory.Faker('md5')
    anonymous = False
    creator = factory.SubFactory(UserFactory)


class CollectionFactory(DjangoModelFactory):
    class Meta:
        model = models.Collection

    title = factory.Faker('catch_phrase')
    user = factory.SubFactory(UserFactory)


class RegistrationFactory(AbstractNodeFactory):

    creator = None
    # Default project is created if not provided
    category = 'project'

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise Exception('Cannot build registration without saving.')

    @classmethod
    def _create(cls, target_class, project=None, is_public=False,
                schema=None, data=None,
                archive=False, embargo=None, registration_approval=None, retraction=None,
                *args, **kwargs):
        user = None
        if project:
            user = project.creator
        user = kwargs.pop('user', None) or kwargs.get('creator') or user or UserFactory()
        kwargs['creator'] = user
        # Original project to be registered
        project = project or target_class(*args, **kwargs)
        if project.has_permission(user, 'admin'):
            project.add_contributor(
                contributor=user,
                permissions=permissions.CREATOR_PERMISSIONS,
                log=False,
                save=False
            )
        project.save()

        # Default registration parameters
        schema = schema or get_default_metaschema()
        data = data or {'some': 'data'}
        auth = Auth(user=user)
        register = lambda: project.register_node(
            schema=schema,
            auth=auth,
            data=data
        )

        def add_approval_step(reg):
            if embargo:
                reg.embargo = embargo
            elif registration_approval:
                reg.registration_approval = registration_approval
            elif retraction:
                reg.retraction = retraction
            else:
                reg.require_approval(reg.creator)
            reg.save()
            reg.sanction.add_authorizer(reg.creator, reg)
            reg.sanction.save()

        with patch('framework.celery_tasks.handlers.enqueue_task'):
            reg = register()
            add_approval_step(reg)
        if not archive:
            with patch.object(reg.archive_job, 'archive_tree_finished', Mock(return_value=True)):
                reg.archive_job.status = ARCHIVER_SUCCESS
                reg.archive_job.save()
                reg.sanction.state = Sanction.APPROVED
                reg.sanction.save()
        models.ArchiveJob(
            src_node=project,
            dst_node=reg,
            initiator=user,
        )
        if is_public:
            reg.is_public = True
        reg.save()
        return reg


class SanctionFactory(DjangoModelFactory):
    class Meta:
        abstract = True

    @classmethod
    def _create(cls, target_class, initiated_by=None, approve=False, *args, **kwargs):
        user = kwargs.pop('user', None) or UserFactory()
        kwargs['initiated_by'] = initiated_by or user
        sanction = super(SanctionFactory, cls)._create(target_class, *args, **kwargs)
        reg_kwargs = {
            'creator': user,
            'user': user,
            sanction.SHORT_NAME: sanction
        }
        RegistrationFactory(**reg_kwargs)
        if not approve:
            sanction.state = Sanction.UNAPPROVED
            sanction.save()
        return sanction

class RetractionFactory(SanctionFactory):
    class Meta:
        model = models.Retraction
    user = factory.SubFactory(UserFactory)

class EmbargoFactory(SanctionFactory):
    class Meta:
        model = models.Embargo
    user = factory.SubFactory(UserFactory)

class RegistrationApprovalFactory(SanctionFactory):
    class Meta:
        model = models.RegistrationApproval
    user = factory.SubFactory(UserFactory)

class EmbargoTerminationApprovalFactory(DjangoModelFactory):

    FACTORY_STRATEGY = factory.base.CREATE_STRATEGY

    @classmethod
    def create(cls, registration=None, user=None, embargo=None, *args, **kwargs):
        if registration:
            if not user:
                user = registration.creator
        else:
            user = user or UserFactory()
            if not embargo:
                embargo = EmbargoFactory(initiated_by=user, state=models.Sanction.APPROVED, approve=True)
                registration = embargo._get_registration()
            else:
                registration = RegistrationFactory(creator=user, user=user, embargo=embargo)
        with mock.patch('osf_models.models.sanctions.TokenApprovableSanction.ask', mock.Mock()):
            approval = registration.request_embargo_termination(Auth(user))
            return approval


class CommentFactory(DjangoModelFactory):
    class Meta:
        model = models.Comment

    content = factory.Sequence(lambda n: 'Comment {0}'.format(n))

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        node = kwargs.pop('node', None) or NodeFactory()
        user = kwargs.pop('user', None) or node.creator
        target = kwargs.pop('target', None) or models.Guid.load(node._id)
        content = kwargs.pop('content', None) or 'Test comment.'
        instance = target_class(
            node=node,
            user=user,
            target=target,
            content=content,
            *args, **kwargs
        )
        if isinstance(target.referent, target_class):
            instance.root_target = target.referent.root_target
        else:
            instance.root_target = target
        return instance

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        node = kwargs.pop('node', None) or NodeFactory()
        user = kwargs.pop('user', None) or node.creator
        target = kwargs.pop('target', None) or models.Guid.load(node._id)
        content = kwargs.pop('content', None) or 'Test comment.'
        instance = target_class(
            node=node,
            user=user,
            target=target,
            content=content,
            *args, **kwargs
        )
        if isinstance(target.referent, target_class):
            instance.root_target = target.referent.root_target
        else:
            instance.root_target = target
        instance.save()
        return instance

