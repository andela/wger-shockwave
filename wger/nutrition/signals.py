'''
A module that is meant to delete cache for nutritional_info once
any changes that will affect the contained calculated information is made.
'''
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from wger.nutrition.models import NutritionPlan, Meal, MealItem
from wger.utils.cache import cache_mapper

SIGNALS_RECEIVED = [post_save, post_delete]
@receiver(SIGNALS_RECEIVED, sender=NutritionPlan)
@receiver(SIGNALS_RECEIVED, sender=Meal)
@receiver(SIGNALS_RECEIVED, sender=MealItem)

def cache_deletion_on_change(sender, instance, **kwargs):
    '''
    Delete cache data for a particular nutrion plan once an add, edit
    or delete occurs on Meal, MealItem classes and the NutritionPlan class.
    '''
    if sender == Meal:
        nutrition_plan_id = instance.plan_id
    elif sender == MealItem:
        nutrition_plan_id = Meal.objects.get(id=instance.meal_id).plan_id
    else:
        nutrition_plan_id = instance.id
    cache.delete(cache_mapper.get_nutritional_info(nutrition_plan_id))
