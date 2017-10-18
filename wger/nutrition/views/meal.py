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

from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext_lazy

from django.views.generic import CreateView, UpdateView
from django.shortcuts import render

from wger.nutrition.forms import MealItemFormSet
from wger.nutrition.models import NutritionPlan, Meal, MealItem
from wger.utils.generic_views import WgerFormMixin

logger = logging.getLogger(__name__)

# ************************
# Meal functions
# ************************


class MealCreateView(WgerFormMixin, CreateView):
    '''
    Generic view to add a new meal to a nutrition plan
    '''

    model = Meal
    fields = '__all__'
    title = ugettext_lazy('Add new meal')
    template_name = 'meal/add.html'
    owner_object = {'pk': 'plan_pk', 'class': NutritionPlan}

    def form_valid(self, form):
        plan = get_object_or_404(
            NutritionPlan, pk=self.kwargs['plan_pk'], user=self.request.user)
        form.instance.plan = plan
        form.instance.order = 1

        # Save the meal object
        self.object = form.save()

        context = self.get_context_data()
        meal_item_formset = context['meal_item']

        if meal_item_formset.is_valid():
            # Retrieve form inputs after validating them
            for meal_item in meal_item_formset:
                cleaned = meal_item.cleaned_data
                amount = cleaned.get('amount')
                weight_unit = cleaned.get('weight_unit')
                ingredient = cleaned.get('ingredient')
                # Check for a valid ingredient and amount
                if amount and ingredient:
                    meal_item = None
                    if weight_unit:
                        meal_item = MealItem(
                            meal=self.object,
                            ingredient=ingredient,
                            weight_unit=weight_unit,
                            order=1,
                            amount=amount
                        )
                    else:
                        meal_item = MealItem(
                            meal=self.object,
                            ingredient=ingredient,
                            order=1,
                            amount=amount
                        )
                    meal_item.save()
                    return HttpResponseRedirect(self.get_success_url())
                else:
                    return HttpResponseRedirect(self.get_success_url())
        else:
            self.object.delete()
            return render(self.request, self.template_name, context)

    def get_success_url(self):
        return self.object.plan.get_absolute_url()

    # Send some additional data to the template
    def get_context_data(self, **kwargs):
        context = super(MealCreateView, self).get_context_data(**kwargs)
        
        if self.request.POST:
            context['ingredient_searchfield'] = self.request.POST.get(
                'ingredient_searchfield', ''
            )
            if context['ingredient_searchfield'] == '':
                post_data = self.request.POST.copy()
                post_data['mealitem_set-0-ingredient'] = ''
                context['meal_item'] = MealItemFormSet(post_data)
            else:
                context['meal_item'] = MealItemFormSet(self.request.POST)
        else:
            context['meal_item'] = MealItemFormSet()

        context['form_action'] = reverse(
            'nutrition:meal:add', kwargs={'plan_pk': self.kwargs['plan_pk']})

        return context


class MealEditView(WgerFormMixin, UpdateView):
    '''
    Generic view to update an existing meal
    '''

    model = Meal
    fields = '__all__'
    title = ugettext_lazy('Edit meal')
    form_action_urlname = 'nutrition:meal:edit'

    def get_success_url(self):
        return self.object.plan.get_absolute_url()


@login_required
def delete_meal(request, id):
    '''
    Deletes the meal with the given ID
    '''

    # Load the meal
    meal = get_object_or_404(Meal, pk=id)
    plan = meal.plan

    # Only delete if the user is the owner
    if plan.user == request.user:
        meal.delete()
        return HttpResponseRedirect(plan.get_absolute_url())
    else:
        return HttpResponseForbidden()
