import pytest

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from website.util import permissions
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PrivateLinkFactory
)

@pytest.fixture(scope='function')
def user():
    return AuthUserFactory()

@pytest.fixture(scope='function')
def read_only_user():
    return AuthUserFactory()

@pytest.fixture(scope='function')
def read_write_user():
    return AuthUserFactory()

@pytest.fixture(scope='function')
def non_contributor():
    return AuthUserFactory()

@pytest.fixture(scope='function')
def public_project(user, read_only_user, read_write_user):
    public_project = ProjectFactory(is_public=True, creator=user)
    public_project.add_contributor(read_only_user, permissions=[permissions.READ])
    public_project.add_contributor(read_write_user, permissions=[permissions.WRITE])
    public_project.save()
    return public_project

@pytest.fixture(scope='function')
def view_only_link(public_project):
    view_only_link = PrivateLinkFactory(name='testlink')
    view_only_link.nodes.add(public_project)
    view_only_link.save()
    return view_only_link

@pytest.mark.django_db
@pytest.mark.usefixtures('user', 'read_only_user', 'read_write_user', 'non_contributor', 'public_project', 'view_only_link')
class TestViewOnlyLinksDetail:

    @pytest.fixture()
    def url(self, public_project, view_only_link):
        return '/{}nodes/{}/view_only_links/{}/'.format(API_BASE, public_project._id, view_only_link._id)

    def test_non_mutating_view_only_links_detail_tests(self, app, user, read_write_user, read_only_user, non_contributor, url, public_project, view_only_link):

    #   test_admin_can_view_vol_detail
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'testlink'

    #   test_read_write_cannot_view_vol_detail
        res = app.get(url, auth=read_write_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_cannot_view_vol_detail
        res = app.get(url, auth=read_only_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_user_cannot_view_vol_detail
        res = app.get(url, auth=non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_view_vol_detail
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

    def test_deleted_vol_not_returned(self, app, user, public_project, view_only_link, url):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'testlink'

        view_only_link.nodes.remove(public_project)
        view_only_link.save()

        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

@pytest.mark.django_db
@pytest.mark.usefixtures('user', 'read_only_user', 'read_write_user', 'non_contributor', 'public_project', 'view_only_link')
class TestViewOnlyLinksUpdate:

    @pytest.fixture()
    def url(self, public_project, view_only_link):
        return '/{}nodes/{}/view_only_links/{}/'.format(API_BASE, public_project._id, view_only_link._id)

    @pytest.fixture()
    def public_project_admin(self, public_project):
        return AuthUserFactory()

    @pytest.fixture()
    def public_project(self, public_project_admin, public_project):
        public_project.add_contributor(public_project_admin, permissions=[permissions.ADMIN])
        return public_project

    @pytest.fixture()
    def public_project_component(self, user, public_project):
        return NodeFactory(is_public=True, creator=user, parent=public_project)

    def test_admin_can_update_vol_name(self, app, user, view_only_link, url):
        assert view_only_link.name == 'testlink'
        assert view_only_link.anonymous == False

        payload = {
            'attributes': {
                'name': 'updated vol name'
            }
        }
        res = app.put_json_api(url, {'data': payload}, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'updated vol name'
        assert res.json['data']['attributes']['anonymous'] == False

    def test_admin_can_update_vol_anonymous(self, app, user, view_only_link, url):
        assert view_only_link.name == 'testlink'
        assert view_only_link.anonymous == False

        payload = {
            'attributes': {
                'anonymous': True
            }
        }
        res = app.put_json_api(url, {'data': payload}, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'testlink'
        assert res.json['data']['attributes']['anonymous'] == True

    def test_cannot_update_vol(self, app, read_write_user, read_only_user, non_contributor, url):

    #   test_read_write_cannot_update_vol
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
            }
        }
        res = app.put_json_api(url, {'data': payload}, auth=read_write_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_cannot_update_vol
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
            }
        }
        res = app.put_json_api(url, {'data': payload}, auth=read_only_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_user_cannot_update_vol
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
            }
        }
        res = app.put_json_api(url, {'data': payload}, auth=non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_update_vol
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
            }
        }
        res = app.put_json_api(url, {'data': payload}, expect_errors=True)
        assert res.status_code == 401

@pytest.mark.django_db
@pytest.mark.usefixtures('user', 'read_only_user', 'read_write_user', 'non_contributor', 'public_project', 'view_only_link')
class TestViewOnlyLinksDelete:

    @pytest.fixture()
    def url(self, public_project, view_only_link):
        return '/{}nodes/{}/view_only_links/{}/'.format(API_BASE, public_project._id, view_only_link._id)

    def test_admin_can_delete_vol(self, app, user, url, view_only_link):
        res = app.delete(url, auth=user.auth)
        view_only_link.reload()
        assert res.status_code == 204
        assert view_only_link.is_deleted == True

    def test_vol_delete(self, app, read_write_user, read_only_user, non_contributor, url):

    #   test_read_write_cannot_delete_vol
        res = app.delete(url, auth=read_write_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_cannot_delete_vol
        res = app.delete(url, auth=read_only_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_user_cannot_delete_vol
        res = app.delete(url, auth=non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_delete_vol
        res = app.delete(url, expect_errors=True)
        assert res.status_code == 401
