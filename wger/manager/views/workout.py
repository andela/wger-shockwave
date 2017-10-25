# -*- coding: utf-8 -*-

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

import logging
import uuid
import datetime
import json

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponseForbidden, HttpResponse
from django.template.context_processors import csrf
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy, ugettext as _
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import DeleteView, UpdateView

from django.contrib.auth.models import User
from wger.core.models import (RepetitionUnit, WeightUnit)
from wger.manager.models import (Workout, WorkoutSession, WorkoutLog, Schedule,
                                 Day, ExportWorkout)
from wger.manager.forms import (WorkoutForm, WorkoutSessionHiddenFieldsForm,
                                WorkoutCopyForm, ExportWorkoutForm)
from wger.utils.generic_views import (WgerFormMixin, WgerDeleteMixin)
from wger.utils.helpers import make_token

logger = logging.getLogger(__name__)


# ************************
# Workout functions
# ************************
@login_required
def overview(request):
    '''
    An overview of all the user's workouts
    '''

    template_data = {}
    import_status = False
    workouts = Workout.objects.filter(user=request.user)
    exported_workouts = ExportWorkout.objects.filter(receiver_id=request.user)
    for workout in exported_workouts:
        user = User.objects.get(pk=workout.sender)
    if exported_workouts:
        import_status = True
    (current_workout,
     schedule) = Schedule.objects.get_current_workout(request.user)
    template_data['workouts'] = workouts
    template_data['current_workout'] = current_workout
    template_data['importworkout'] = import_status
    template_data['exportedworkouts'] = exported_workouts

    return render(request, 'workout/overview.html', template_data)


def view(request, pk):
    '''
    Show the workout with the given ID
    '''
    template_data = {}
    workout = get_object_or_404(Workout, pk=pk)
    user = workout.user
    is_owner = request.user == user
    export_workout_state = False

    if not is_owner and not user.userprofile.ro_access:
        return HttpResponseForbidden()

    canonical = workout.canonical_representation
    if 'exercise_list' in str(canonical):
        export_workout_state = True
    uid, token = make_token(user)

    # Create the backgrounds that show what muscles the workout will work on
    muscles_front = []
    muscles_back = []
    for i in canonical['muscles']['front']:
        if i not in muscles_front:
            muscles_front.append(
                'images/muscles/main/muscle-{0}.svg'.format(i))
    for i in canonical['muscles']['back']:
        if i not in muscles_back:
            muscles_back.append('images/muscles/main/muscle-{0}.svg'.format(i))

    for i in canonical['muscles']['frontsecondary']:
        if i not in muscles_front and i not in canonical['muscles']['front']:
            muscles_front.append(
                'images/muscles/secondary/muscle-{0}.svg'.format(i))
    for i in canonical['muscles']['backsecondary']:
        if i not in muscles_back and i not in canonical['muscles']['back']:
            muscles_back.append(
                'images/muscles/secondary/muscle-{0}.svg'.format(i))

    # Append the silhouette of the human body as the last entry so the browser
    # renders it in the background
    muscles_front.append('images/muscles/muscular_system_front.svg')
    muscles_back.append('images/muscles/muscular_system_back.svg')

    template_data['workout'] = workout
    template_data['muscle_backgrounds_front'] = muscles_front
    template_data['muscle_backgrounds_back'] = muscles_back
    template_data['uid'] = uid
    template_data['token'] = token
    template_data['is_owner'] = is_owner
    template_data['owner_user'] = user
    template_data['show_shariff'] = is_owner
    template_data['export_workout_state'] = export_workout_state

    return render(request, 'workout/view.html', template_data)


@login_required
def copy_workout(request, pk):
    '''
    Makes a copy of a workout
    '''

    workout = get_object_or_404(Workout, pk=pk)
    user = workout.user
    is_owner = request.user == user

    if not is_owner and not user.userprofile.ro_access:
        return HttpResponseForbidden()

    # Process request
    if request.method == 'POST':
        workout_form = WorkoutCopyForm(request.POST)

        if workout_form.is_valid():
            
            # Copy workout
            days = workout.day_set.all()

            workout_copy = workout
            workout_copy.pk = None
            workout_copy.comment = workout_form.cleaned_data['comment']
            workout_copy.user = request.user
            workout_copy.save()
            CopyWorkout().duplicate_workout(days, workout_copy)

            return HttpResponseRedirect(
                reverse('manager:workout:view', kwargs={'pk': workout.id}))
    else:
        workout_form = WorkoutCopyForm({'comment': workout.comment})

        template_data = {}
        template_data.update(csrf(request))
        template_data['title'] = _('Copy workout')
        template_data['form'] = workout_form
        template_data['form_action'] = reverse(
            'manager:workout:copy', kwargs={'pk': workout.id})
        template_data['form_fields'] = [workout_form['comment']]
        template_data['submit_text'] = _('Copy')
        template_data[
            'extend_template'] = 'base_empty.html' if request.is_ajax() else 'base.html'

        return render(request, 'form.html', template_data)


@login_required
def add(request):
    '''
    Add a new workout and redirect to its page
    '''
    workout = Workout()
    workout.user = request.user
    workout.save()

    return HttpResponseRedirect(workout.get_absolute_url())

@login_required
def exportworkout(request, pk):
    '''
    Export workout and redirect to workout page
    :param exercise:
    :param pk: ID of workout being exported
    '''
    workout = get_object_or_404(Workout, pk=pk)

    if request.method == 'POST':
        workout_export = ExportWorkout()
        workout_export.sender = request.user.id
        workout_export.receiver = User.objects.get(username=request.POST['receiver'])
        workout_export.workout = workout
        workout_export.name = request.user.username
        workout_export.save()
        
        return HttpResponseRedirect(reverse('manager:workout:view', kwargs={'pk':workout.id}))

    template_data = {}
    template_data['title'] = _('Select User to Send Workout to:')
    template_data['form'] = ExportWorkoutForm()
    template_data['form_action'] = reverse('manager:workout:exportworkout', 
        kwargs={'pk':workout.id})
    template_data['submit_text'] = _('Send')
    template_data['extend_template'] = 'base_empty.html' if request.is_ajax() else 'base.html'
    
    return render(request, 'form.html', template_data)

@login_required
def importworkout(request, pk):
    '''
    Import Workout and redirect to list of workouts
    :param request:
    :param pk: ID of the workout being imported
    '''
    workout_export = get_object_or_404(ExportWorkout, pk=pk)
    imported_workout = get_object_or_404(Workout, pk=workout_export.workout_id)
    new_workout = Workout.objects.create(pk=None, user=request.user)
    new_workout.comment = imported_workout.comment
    new_workout.save()
    days = imported_workout.day_set.all()
    CopyWorkout().duplicate_workout(days, new_workout)
    workout_export.delete()

    return HttpResponseRedirect(reverse('manager:workout:overview'))


class CopyWorkout():
    '''
    Class to copy workouts
    '''
    def duplicate_workout(self, days, workout_copy):
        '''
        Duplicate workout with days, sets and exercises
        :params days: The days chosen to perform the exercises
        :params workout_copy: The copy of the workout
        '''
        # Copy the days
        for day in days:
            sets = day.set_set.all()
            day_copy = day
            days_of_week = [i for i in day.day.all()]
            day_copy.pk = None
            day_copy.training = workout_copy
            day_copy.save()
            for i in days_of_week:
                day_copy.day.add(i)
            day_copy.save()

            # Copy the sets
            for current_set in sets:
                current_set_id = current_set.id
                exercises = current_set.exercises.all()

                current_set_copy = current_set
                current_set_copy.pk = None
                current_set_copy.exerciseday = day_copy
                current_set_copy.save()

                # Exercises has Many2Many relationship
                current_set_copy.exercises = exercises

                # Go through the exercises
                for exercise in exercises:
                    settings = exercise.setting_set.filter(
                        set_id=current_set_id)

                    # Copy the settings
                    for setting in settings:
                        setting_copy = setting
                        setting_copy.pk = None
                        setting_copy.set = current_set_copy
                        setting_copy.save()



class WorkoutDeleteView(WgerDeleteMixin, LoginRequiredMixin, DeleteView):
    '''
    Generic view to delete a workout routine
    '''

    model = Workout
    fields = ('comment', )
    success_url = reverse_lazy('manager:workout:overview')
    messages = ugettext_lazy('Successfully deleted')

    def get_context_data(self, **kwargs):
        context = super(WorkoutDeleteView, self).get_context_data(**kwargs)
        context['form_action'] = reverse(
            'manager:workout:delete', kwargs={'pk': self.object.id})
        context['title'] = _(u'Delete {0}?').format(self.object)

        return context


class WorkoutEditView(WgerFormMixin, LoginRequiredMixin, UpdateView):
    '''
    Generic view to update an existing workout routine
    '''

    model = Workout
    form_class = WorkoutForm
    form_action_urlname = 'manager:workout:edit'

    def get_context_data(self, **kwargs):
        context = super(WorkoutEditView, self).get_context_data(**kwargs)
        context['title'] = _(u'Edit {0}').format(self.object)

        return context


class LastWeightHelper:
    '''
    Small helper class to retrieve the last workout log for a certain
    user, exercise and repetition combination.
    '''
    user = None
    last_weight_list = {}

    def __init__(self, user):
        self.user = user

    def get_last_weight(self, exercise, reps, default_weight):
        '''
        Returns an emtpy string if no entry is found

        :param exercise:
        :param reps:
        :param default_weight:
        :return: WorkoutLog or '' if none is found
        '''
        key = (self.user.pk, exercise.pk, reps, default_weight)
        if self.last_weight_list.get(key) is None:
            last_log = WorkoutLog.objects.filter(
                user=self.user, exercise=exercise, reps=reps).order_by('-date')
            default_weight = '' if default_weight is None else default_weight
            weight = last_log[
                0].weight if last_log.exists() else default_weight
            self.last_weight_list[key] = weight

        return self.last_weight_list.get(key)


@login_required
def timer(request, day_pk):
    '''
    The timer view ("gym mode") for a workout
    '''

    day = get_object_or_404(Day, pk=day_pk, training__user=request.user)
    canonical_day = day.canonical_representation
    context = {}
    step_list = []
    last_log = LastWeightHelper(request.user)

    # Go through the workout day and create the individual 'pages'
    for set_dict in canonical_day['set_list']:

        if not set_dict['is_superset']:
            for exercise_dict in set_dict['exercise_list']:
                exercise = exercise_dict['obj']
                for key, element in enumerate(exercise_dict['reps_list']):
                    reps = exercise_dict['reps_list'][key]
                    rep_unit = exercise_dict['repetition_units'][key]
                    weight_unit = exercise_dict['weight_units'][key]
                    default_weight = last_log.get_last_weight(
                        exercise, reps, exercise_dict['weight_list'][key])

                    step_list.append({
                        'current_step': uuid.uuid4().hex,
                        'step_percent': 0,
                        'step_nr': len(step_list) + 1,
                        'exercise': exercise,
                        'type': 'exercise',
                        'reps': reps,
                        'rep_unit': rep_unit,
                        'weight': default_weight,
                        'weight_unit': weight_unit
                    })
                    if request.user.userprofile.timer_active:
                        step_list.append({
                            'current_step':
                            uuid.uuid4().hex,
                            'step_percent':
                            0,
                            'step_nr':
                            len(step_list) + 1,
                            'type':
                            'pause',
                            'time':
                            request.user.userprofile.timer_pause
                        })

        # Supersets need extra work to group the exercises and reps together
        else:
            total_reps = len(set_dict['exercise_list'][0]['reps_list'])
            for i in range(0, total_reps):
                for exercise_dict in set_dict['exercise_list']:
                    reps = exercise_dict['reps_list'][i]
                    rep_unit = exercise_dict['repetition_units'][i]
                    weight_unit = exercise_dict['weight_units'][i]
                    default_weight = exercise_dict['weight_list'][i]
                    exercise = exercise_dict['obj']

                    step_list.append({
                        'current_step':
                        uuid.uuid4().hex,
                        'step_percent':
                        0,
                        'step_nr':
                        len(step_list) + 1,
                        'exercise':
                        exercise,
                        'type':
                        'exercise',
                        'reps':
                        reps,
                        'rep_unit':
                        rep_unit,
                        'weight_unit':
                        weight_unit,
                        'weight':
                        last_log.get_last_weight(exercise, reps,
                                                 default_weight)
                    })

                if request.user.userprofile.timer_active:
                    step_list.append({
                        'current_step': uuid.uuid4().hex,
                        'step_percent': 0,
                        'step_nr': len(step_list) + 1,
                        'type': 'pause',
                        'time': 90
                    })

    # Remove the last pause step as it is not needed. If the list is empty,
    # because the user didn't add any repetitions to any exercise, do nothing
    try:
        step_list.pop()
    except IndexError:
        pass

    # Go through the page list and calculate the correct value for step_percent
    for i, s in enumerate(step_list):
        step_list[i]['step_percent'] = (i + 1) * 100.0 / len(step_list)

    # Depending on whether there is already a workout session for today, update
    # the current one or create a new one (this will be the most usual case)
    if WorkoutSession.objects.filter(
            user=request.user, date=datetime.date.today()).exists():
        session = WorkoutSession.objects.get(
            user=request.user, date=datetime.date.today())
        url = reverse('manager:session:edit', kwargs={'pk': session.pk})
        session_form = WorkoutSessionHiddenFieldsForm(instance=session)
    else:
        today = datetime.date.today()
        url = reverse(
            'manager:session:add',
            kwargs={
                'workout_pk': day.training_id,
                'year': today.year,
                'month': today.month,
                'day': today.day
            })
        session_form = WorkoutSessionHiddenFieldsForm()

    # Render template
    context['day'] = day
    context['step_list'] = step_list
    context['canonical_day'] = canonical_day
    context['workout'] = day.training
    context['session_form'] = session_form
    context['form_action'] = url
    context['weight_units'] = WeightUnit.objects.all()
    context['repetition_units'] = RepetitionUnit.objects.all()
    return render(request, 'workout/timer.html', context)

@login_required
def get_users(request):
    if request.is_ajax():
        q = request.GET.get('term', '')
        users = User.objects.filter(username__icontains = q )[:20]
        results = []
        for user in users:
            if user == request.user:
                continue;
            else:
                user_json = {}
                user_json['label'] = user.username            
                user_json['value'] = user.username
                results.append(user_json)
        data = json.dumps({'suggestions':results})
        mimetype = 'application/json'
    else:
        data = 'fail'
        mimetype = 'application/json'
    return HttpResponse(data, mimetype)
