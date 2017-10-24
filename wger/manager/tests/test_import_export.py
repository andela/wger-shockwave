# This file is part of wger Workout Manager.
#
# wger Workout Manager is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wger Workout Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from wger.core.tests.base_testcase import WorkoutManagerTestCase
from wger.manager.models import Workout, ExportWorkout

class ExportImportWorkout(WorkoutManagerTestCase):
    '''
    Test the import export feature of workouts in the wger application
    '''

    def export_importer_workout(self):
        '''
        Create Objects for testing the export import functions
        '''
        export_user = User.objects.create_user(username='example', password='example_password')
        import_user = User.objects.create_user(username='importer', password='example_password2')
        workout_to_export = Workout(user_id=export_user.pk, comment='test_workout')
        workout_to_export.save()
        return [export_user, import_user, workout_to_export]

    def test_exported_fields(self):
        '''
        Test that an export passes in the right values in the table, for the sender
        receiver and workout to export
        '''
        instance_list = self.export_importer_workout()
        exporter = instance_list[0]
        importer = instance_list[1]
        workout = instance_list[2]
        self.client.login(username='example', password='example_password')
        self.client.post(reverse(
            'manager:workout:exportworkout',
            kwargs={'pk': workout.pk}), {'receiver': importer.pk, 'user': exporter})
        exported_workout = ExportWorkout.objects.filter(workout_id=workout.pk).first()
        self.assertEqual(exported_workout.sender, exporter.pk)
        self.assertEqual(exported_workout.receiver_id, importer.pk)
        self.assertEqual(exported_workout.workout_id, workout.pk)

    def test_import_button_shown(self):
        '''
        Test that an import button is shown on the view of the importer
        '''
        instance_list = self.export_importer_workout()
        exporter = instance_list[0]
        importer = instance_list[1]
        workout = instance_list[2]
        self.client.login(username='importer', password='example_password2')
        get_response = self.client.get(reverse('manager:workout:overview'))
        self.assertNotContains(get_response, 'Import Workout')
        self.client.login(username='example', password='example_password')
        self.client.post(reverse(
            'manager:workout:exportworkout',
            kwargs={'pk': workout.pk}), {'receiver': importer.pk, 'user': exporter})
        self.client.login(username='importer', password='example_password2')
        get_response = self.client.get(reverse('manager:workout:overview'))
        self.assertContains(get_response, 'Import Workout')

    def test_import_workout(self):
        '''
        Test that the import adds a workout to the user and that the import
        button disappears
        '''
        instance_list = self.export_importer_workout()
        exporter = instance_list[0]
        importer = instance_list[1]
        workout = instance_list[2]
        workouts_for_importer = Workout.objects.filter(user_id=importer.pk)
        self.assertEqual(0, len(workouts_for_importer))
        self.client.login(username='example', password='example_password')
        self.client.post(reverse(
            'manager:workout:exportworkout',
            kwargs={'pk': workout.pk}), {'receiver': importer.pk, 'user': exporter})
        self.client.login(username='importer', password='example_password2')
        exported_workout = ExportWorkout.objects.filter(workout_id=workout.pk).first()
        self.client.post(reverse('manager:workout:importworkout',
                                 kwargs={'pk': exported_workout.pk}))
        workouts_for_importer = Workout.objects.filter(user_id=importer.pk)
        self.assertEqual(1, len(workouts_for_importer))
        workout_added = workouts_for_importer.first()
        self.assertEqual(workout_added.comment, workout.comment)
        get_response = self.client.get(reverse('manager:workout:overview'))
        self.assertNotContains(get_response, 'Import Workout')

    def test_export_button_tooltip(self):
        '''
        Test that a workout without exercises will render a tooltip and that
        it will not have a link for exporting a workout
        Test that a workout with exercises will render import button with a link,
        and will not render a tooltip
        '''
        workout = self.export_importer_workout()[2]
        self.client.login(username='example', password='example_password')
        get_response = self.client.get(
            reverse('manager:workout:view', kwargs={'pk': workout.pk}))
        self.assertContains(get_response, 'You can\'t export workouts that have no exercise!')
        self.assertNotContains(
            get_response, '/en/workout/'+ str(workout.pk) +'/exportworkout/')
        workout1 = Workout.objects.filter(id=1).first()
        second_get_response = self.client.get(
            reverse('manager:workout:view', kwargs={'pk': workout1.pk}))
        self.assertNotContains(
            second_get_response, 'You can\'t export workouts that have no exercise!')
        self.assertContains(
            second_get_response, '/en/workout/'+ str(workout1.id) +'/exportworkout/')
