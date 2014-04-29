from django.test import TestCase
from django.core.exceptions import PermissionDenied, ValidationError

from nose.tools import raises

from projects.tests.model_factories import ProjectF, UserGroupF, UserF
from observationtypes.tests.model_factories import (
    ObservationTypeFactory, TextFieldFactory, NumericFieldFactory
)
from core.exceptions import MalformedRequestData

from ..models import Location, Observation, Comment

from .model_factories import (
    LocationFactory, ObservationFactory, CommentFactory
)


class IsContributorTest(TestCase):
    def setUp(self):
        self.creator = UserF.create()
        self.observation = ObservationFactory.create(**{
            'creator': self.creator
        })

    def test_basic_with_creator(self):
        self.assertTrue(self.observation.is_contributor(self.creator))

    def test_basic_with_some_dude(self):
        some_dude = UserF.create()
        self.assertFalse(self.observation.is_contributor(some_dude))

    def test_updated_with_creator(self):
        updator = UserF.create()
        ObservationFactory.create(**{
            'creator': updator
        })
        self.assertTrue(self.observation.is_contributor(self.creator))

    def test_updated_with_updator(self):
        updator = UserF.create()
        self.observation.update(
            attributes={'key': 'new', 'version': 1},
            creator=updator
        )
        self.assertTrue(self.observation.is_contributor(updator))

    def test_updated_with_some_dude(self):
        some_dude = UserF.create()
        updator = UserF.create()
        self.observation.update(
            attributes={'key': 'new', 'version': 1},
            creator=updator
        )
        self.assertFalse(self.observation.is_contributor(some_dude))


class LocationTest(TestCase):
    def setUp(self):
        self.admin = UserF.create()

        self.project1 = ProjectF(**{
            'admins': UserGroupF(add_users=[self.admin]),
        })
        self.project2 = ProjectF(**{
            'admins': UserGroupF(add_users=[self.admin]),
        })
        self.public_location = LocationFactory(**{
            'private': False
        })
        self.private_location = LocationFactory(**{
            'private': True
        })
        self.private_for_project_location = LocationFactory(**{
            'private': True,
            'private_for_project': self.project1
        })

    # ########################################################################
    #
    # LOCATIONS
    #
    # ########################################################################

    def test_get_locations_for_project1_with_admin(self):
        locations = Location.objects.get_list(self.admin, self.project1.id)
        self.assertEqual(len(locations), 2)

    def test_get_locations_for_project2_with_admin(self):
        locations = Location.objects.get_list(self.admin, self.project2.id)
        self.assertEqual(len(locations), 1)

    def test_get_public_location_for_project1_with_admin(self):
        location = Location.objects.get_single(
            self.admin, self.project1.id, self.public_location.id)
        self.assertEqual(location, self.public_location)

    def test_get_project_location_for_project1_with_admin(self):
        location = Location.objects.get_single(
            self.admin, self.project1.id, self.private_for_project_location.id)
        self.assertEqual(location, self.private_for_project_location)

    @raises(PermissionDenied)
    def test_get_private_location_for_project1_with_admin(self):
        Location.objects.get_single(
            self.admin, self.project1.id, self.private_location.id)

    def test_get_public_location_for_project2_with_admin(self):
        location = Location.objects.get_single(
            self.admin, self.project2.id, self.public_location.id)
        self.assertEqual(location, self.public_location)

    @raises(PermissionDenied)
    def test_get_project_location_for_project2_with_admin(self):
        Location.objects.get_single(
            self.admin, self.project2.id, self.private_for_project_location.id)

    @raises(PermissionDenied)
    def test_get_private_location_for_project2_with_admin(self):
        Location.objects.get_single(
            self.admin, self.project2.id, self.private_location.id)

    # ########################################################################
    #
    # OBSERVATIONS
    #
    # ########################################################################


class ObservationTest(TestCase):
    @raises(Observation.DoesNotExist)
    def test_delete_observation(self):
        observation = ObservationFactory()
        observation.delete()
        Observation.objects.get(pk=observation.id)

    def test_create_observation(self):
        creator = UserF()
        location = LocationFactory()
        observationtype = ObservationTypeFactory()
        TextFieldFactory(**{
            'key': 'text',
            'observationtype': observationtype
        })
        NumericFieldFactory(**{
            'key': 'number',
            'observationtype': observationtype
        })
        data = {'text': 'Text', 'number': 12}
        observation = Observation.create(
            attributes=data, creator=creator, location=location,
            observationtype=observationtype, project=observationtype.project
        )
        self.assertEqual(observation.attributes, data)

    def test_update_observation(self):
        observationtype = ObservationTypeFactory()
        TextFieldFactory(**{
            'key': 'text',
            'observationtype': observationtype
        })
        NumericFieldFactory(**{
            'key': 'number',
            'observationtype': observationtype
        })

        observation = ObservationFactory.create(**{
            'attributes': {'text': 'Text', 'number': 12},
            'observationtype': observationtype,
            'project': observationtype.project
        })

        updater = UserF()
        update = {'text': 'Udpated Text', 'number': 13, 'version': 1}
        observation.update(attributes=update, creator=updater)

        # ref_observation = Observation.objects.get(pk=observation.id)
        self.assertEqual(
            observation.attributes,
            {'text': 'Udpated Text', 'number': '13'}
        )
        self.assertEqual(observation.version, 2)

    @raises(MalformedRequestData)
    def test_update_observation_without_version(self):
        creator = UserF()
        location = LocationFactory()
        observationtype = ObservationTypeFactory()
        TextFieldFactory(**{
            'key': 'text',
            'observationtype': observationtype
        })
        NumericFieldFactory(**{
            'key': 'number',
            'observationtype': observationtype
        })
        data = {'text': 'Text', 'number': 12}
        observation = Observation.create(
            attributes=data, creator=creator, location=location,
            observationtype=observationtype, project=observationtype.project
        )

        updater = UserF()
        update = {'text': 'Udpated Text', 'number': 13}
        observation.update(attributes=update, creator=updater)

        ref_observation = Observation.objects.get(pk=observation.id)
        self.assertEqual(
            ref_observation.attributes,
            data
        )
        self.assertEqual(ref_observation.current_data.version, 1)

    def test_update_observation_with_conflict(self):
        creator = UserF()

        location = LocationFactory()
        observationtype = ObservationTypeFactory()
        TextFieldFactory(**{
            'key': 'text',
            'observationtype': observationtype
        })
        NumericFieldFactory(**{
            'key': 'number',
            'observationtype': observationtype
        })
        data = {'text': 'Text', 'number': 12}
        observation = Observation.create(
            attributes=data, creator=creator, location=location,
            observationtype=observationtype, project=observationtype.project
        )

        updater = UserF()
        update = {'text': 'Udpated Text', 'number': 13, 'version': 1}
        observation.update(attributes=update, creator=updater)

        updater2 = UserF()
        update2 = {'number': 5, 'version': 1}
        observation.update(attributes=update2, creator=updater2)

        ref_observation = Observation.objects.get(pk=observation.id)
        self.assertEqual(ref_observation.status, 'review')
        self.assertEqual(ref_observation.version, 2)

    @raises(MalformedRequestData)
    def test_update_observation_with_wrong_version(self):
        creator = UserF()
        location = LocationFactory()
        observationtype = ObservationTypeFactory()
        TextFieldFactory(**{
            'key': 'text',
            'observationtype': observationtype
        })
        NumericFieldFactory(**{
            'key': 'number',
            'observationtype': observationtype
        })
        data = {'text': 'Text', 'number': 12}
        observation = Observation.create(
            attributes=data, creator=creator, location=location,
            observationtype=observationtype, project=observationtype.project
        )

        updater = UserF()
        update = {'text': 'Udpated Text', 'number': 13, 'version': 3}
        observation.update(attributes=update, creator=updater)

        ref_observation = Observation.objects.get(pk=observation.id)
        self.assertEqual(
            ref_observation.attributes,
            data
        )
        self.assertEqual(ref_observation.version, 1)

    @raises(ValidationError)
    def test_update_invalid_observation(self):
        creator = UserF()
        location = LocationFactory()
        observationtype = ObservationTypeFactory()
        TextFieldFactory(**{
            'key': 'text',
            'observationtype': observationtype
        })
        NumericFieldFactory(**{
            'key': 'number',
            'observationtype': observationtype
        })
        data = {'text': 'Text', 'number': 12}
        observation = Observation.create(
            attributes=data, creator=creator, location=location,
            observationtype=observationtype, project=observationtype.project
        )

        updater = UserF()
        update = {'text': 'Udpated Text', 'number': 'abc', 'version': 1}
        observation.update(attributes=update, creator=updater)

        self.assertEqual(observation.attributes, data)
        self.assertEqual(observation.version, 1)

    @raises(ValidationError)
    def test_create_invalid_observation(self):
        creator = UserF()
        location = LocationFactory()
        observationtype = ObservationTypeFactory()
        TextFieldFactory(**{
            'key': 'text',
            'observationtype': observationtype
        })
        NumericFieldFactory(**{
            'key': 'number',
            'observationtype': observationtype
        })
        data = {'text': 'Text', 'number': 'abc'}
        Observation.create(
            attributes=data, creator=creator, location=location,
            observationtype=observationtype, project=observationtype.project
        )

    @raises(ValidationError)
    def test_create_invalid_observation_with_empty_textfield(self):
        creator = UserF()
        location = LocationFactory()
        observationtype = ObservationTypeFactory()
        TextFieldFactory(**{
            'key': 'text',
            'required': True,
            'observationtype': observationtype
        })
        NumericFieldFactory(**{
            'key': 'number',
            'observationtype': observationtype
        })
        data = {'number': 1000}
        Observation.create(
            attributes=data, creator=creator, location=location,
            observationtype=observationtype, project=observationtype.project
        )

    @raises(ValidationError)
    def test_create_invalid_observation_with_zero_textfield(self):
        creator = UserF()
        location = LocationFactory()
        observationtype = ObservationTypeFactory()
        TextFieldFactory(**{
            'key': 'text',
            'required': True,
            'observationtype': observationtype
        })
        NumericFieldFactory(**{
            'key': 'number',
            'observationtype': observationtype
        })
        data = {'text': '', 'number': 1000}
        Observation.create(
            attributes=data, creator=creator, location=location,
            observationtype=observationtype, project=observationtype.project
        )

    @raises(ValidationError)
    def test_create_invalid_observation_with_empty_number(self):
        creator = UserF()
        location = LocationFactory()
        observationtype = ObservationTypeFactory()
        TextFieldFactory(**{
            'key': 'text',
            'observationtype': observationtype
        })
        NumericFieldFactory(**{
            'key': 'number',
            'required': True,
            'observationtype': observationtype
        })
        data = {'text': 'bla'}
        Observation.create(
            attributes=data, creator=creator, location=location,
            observationtype=observationtype, project=observationtype.project
        )

    # ########################################################################
    #
    # COMMENTS
    #
    # ########################################################################


class CommentTest(TestCase):
    @raises(Comment.DoesNotExist)
    def test_delete_comment(self):
        comment = CommentFactory()
        comment.delete()
        Comment.objects.get(pk=comment.id)