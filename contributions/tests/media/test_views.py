import json

from PIL import Image
from StringIO import StringIO

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile

from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.renderers import JSONRenderer

from projects.tests.model_factories import UserF, ProjectF

from contributions.views import (
    MediaFileListAbstractAPIView, AllContributionsMediaAPIView
)

from ..model_factories import ObservationFactory
from .model_factories import ImageFileFactory, get_image

class MediaFileAbstractListAPIViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = UserF.create()
        self.creator = UserF.create()
        self.project = ProjectF(
            add_admins=[self.admin],
            add_contributors=[self.creator]
        )

        self.contribution = ObservationFactory.create(
            **{'project': self.project}
        )

        # self.image_file = ImageFileFactory.create(
        #     **{'contribution': self.contribution}
        # )

    def render(self, response):
        response.accepted_renderer = JSONRenderer()
        response.accepted_media_type = 'application/json'
        response.renderer_context = {'blah': 'blubb'}
        return response.render()

    def test_get_list_and_respond(self):
        ImageFileFactory.create_batch(5, **{'contribution': self.contribution})

        url = reverse(
            'api:project_media',
            kwargs={
                'project_id': self.project.id,
                'contribution_id': self.contribution.id
            }
        )

        request = self.factory.get(url)
        view = MediaFileListAbstractAPIView()
        view.request = request

        response = self.render(
            view.get_list_and_respond(self.admin, self.contribution)
        )
        self.assertEqual(len(json.loads(response.content)), 5)

    def test_create_and_respond(self):
        url = reverse(
            'api:project_media',
            kwargs={
                'project_id': self.project.id,
                'contribution_id': self.contribution.id
            }
        )

        data = {
            'name': 'A test image',
            'description': 'Test image description',
            'file': get_image()
        }

        request = self.factory.post(url, data)
        request.user = UserF.create()
        view = MediaFileListAbstractAPIView()
        view.request = request

        response = self.render(
            view.create_and_respond(self.admin, self.contribution)
        )

        response_json = json.loads(response.content)
        self.assertEqual(
            response_json.get('name'),
            data.get('name')
        )
        self.assertEqual(
            response_json.get('description'),
            data.get('description')
        )
        self.assertEqual(
            response_json.get('creator').get('display_name'),
            request.user.display_name
        )


class AllContributionsMediaAPIViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = UserF.create()
        self.creator = UserF.create()
        self.viewer = UserF.create()
        self.project = ProjectF(
            add_admins=[self.admin],
            add_contributors=[self.creator]
        )

        self.contribution = ObservationFactory.create(
            **{'project': self.project, 'creator': self.creator}
        )

        ImageFileFactory.create_batch(5, **{'contribution': self.contribution})

    def get(self, user):
        url = reverse(
            'api:project_media',
            kwargs={
                'project_id': self.project.id,
                'contribution_id': self.contribution.id
            }
        )
        
        request = self.factory.get(url)
        force_authenticate(request, user)
        view = AllContributionsMediaAPIView.as_view()
        return view(
            request,
            project_id=self.project.id,
            contribution_id=self.contribution.id
        ).render()

    def post(self, user, data=None):
        if data is None:
            data = {
                'name': 'A test image',
                'description': 'Test image description',
                'file': get_image()
            }

        url = reverse(
            'api:project_media',
            kwargs={
                'project_id': self.project.id,
                'contribution_id': self.contribution.id
            }
        )
        
        request = self.factory.post(url, data)
        force_authenticate(request, user)
        view = AllContributionsMediaAPIView.as_view()
        return view(
            request,
            project_id=self.project.id,
            contribution_id=self.contribution.id
        ).render()

    def test_get_images_with_admin(self):
        response = self.get(self.admin)
        self.assertEqual(response.status_code, 200)

    def test_get_images_with_contributor(self):
        response = self.get(self.creator)
        self.assertEqual(response.status_code, 200)

    def test_get_images_with_some_dude(self):
        response = self.get(UserF.create())
        self.assertEqual(response.status_code, 404)

    def test_get_images_with_anonymous(self):
        response = self.get(AnonymousUser())
        self.assertEqual(response.status_code, 404)

    def test_upload_image_with_admin(self):
        response = self.post(self.admin)
        self.assertEqual(response.status_code, 201)

    def test_upload_image_with_contributor(self):
        response = self.post(self.creator)
        self.assertEqual(response.status_code, 201)

    def test_upload_image_with_some_dude(self):
        response = self.post(UserF.create())
        self.assertEqual(response.status_code, 404)

    def test_upload_image_with_anonymous(self):
        response = self.post(AnonymousUser())
        self.assertEqual(response.status_code, 404)

    def test_upload_unsupported_file_format(self):
        xyz_file = StringIO()
        xyz = Image.new('RGBA', size=(50,50), color=(256,0,0))
        xyz.save(xyz_file, 'png')
        xyz_file.seek(0)

        data = {
            'name': 'A test image',
            'description': 'Test image description',
            'file': ContentFile(xyz_file.read(), 'test.xyz')
        }

        response = self.post(self.admin, data=data)
        self.assertEqual(response.status_code, 400)

