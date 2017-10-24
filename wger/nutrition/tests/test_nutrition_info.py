'''
Tests the cache operation for calculated nutrition information
'''
from django.contrib.auth.models import User
from django.core.cache import cache
from wger.core.tests.base_testcase import WorkoutManagerTestCase
from wger.nutrition.models import NutritionPlan, Meal, MealItem
from wger.utils.cache import cache_mapper
from wger.core.models import Language

class NutritionaCacheTestCase(WorkoutManagerTestCase):
    '''
    Test cache is deleted once data for calculation of the nutritonal information
    changes. Data is derived from the Meal and Meal Item classes and stored to a
    parent object of the NutritionPlan class
    '''

    def create_nutrition_plan(self):
        '''
        Create a nutrition plan and set dummy attributes that are required
        Create meal and set dummy attributes that are required
        Create meal item and set dummy attributes that are required
        '''
        nutrition_plan = NutritionPlan()
        nutrition_plan.user = User.objects.create_user(username='example_user_1')
        nutrition_plan.language = Language.objects.get(short_name="en")
        nutrition_plan.save()
        meal = Meal()
        meal.plan = nutrition_plan
        meal.order = 1
        meal.save()
        meal_item = MealItem()
        meal_item.meal = meal
        meal_item.amount = 1
        meal_item.ingredient_id = 1
        meal_item.order = 1
        test_objects = [nutrition_plan, meal, meal_item]
        return test_objects

    def test_cache_setting(self):
        '''
        Test that a cache is set once the nutritional information is called
        '''
        nutrition_object = self.create_nutrition_plan()[0]
        self.assertFalse(cache.get(cache_mapper.get_nutritional_info(nutrition_object)))
        nutrition_object.get_nutritional_values()
        self.assertTrue(cache.get(cache_mapper.get_nutritional_info(nutrition_object)))

    def test_nutrition_save_delete(self):
        '''
        Test that the cache is deleted once a nutrition plan undergoes a save or
        delete operation
        '''
        nutrition_object = self.create_nutrition_plan()[0]
        nutrition_object.get_nutritional_values()
        self.assertTrue(cache.get(cache_mapper.get_nutritional_info(nutrition_object)))
        nutrition_object.save()
        self.assertFalse(cache.get(cache_mapper.get_nutritional_info(nutrition_object)))
        nutrition_object.get_nutritional_values()
        self.assertTrue(cache.get(cache_mapper.get_nutritional_info(nutrition_object)))
        nutrition_object.delete()
        self.assertFalse(cache.get(cache_mapper.get_nutritional_info(nutrition_object)))

    def test_meal_save_delete(self):
        '''
        Test that the cache is deleted once a meal undergoes a save or delete operation
        '''
        test_object_list = self.create_nutrition_plan()
        nutritional_object = test_object_list[0]
        meal = test_object_list[1]
        nutritional_object.get_nutritional_values()
        self.assertTrue(cache.get(cache_mapper.get_nutritional_info(nutritional_object)))
        meal.save()
        self.assertFalse(cache.get(cache_mapper.get_nutritional_info(nutritional_object)))
        nutritional_object.get_nutritional_values()
        self.assertTrue(cache.get(cache_mapper.get_nutritional_info(nutritional_object)))
        meal.delete()
        self.assertFalse(cache.get(cache_mapper.get_nutritional_info(nutritional_object)))

    def test_meal_item_save_delete(self):
        '''
        Test that the cache is deleted once a meal item undergoes a save or delete operation
        '''
        test_object_list = self.create_nutrition_plan()
        nutritional_object = test_object_list[0]
        meal_item = test_object_list[2]
        nutritional_object.get_nutritional_values()
        self.assertTrue(cache.get(cache_mapper.get_nutritional_info(nutritional_object)))
        meal_item.save()
        self.assertFalse(cache.get(cache_mapper.get_nutritional_info(nutritional_object)))
        nutritional_object.get_nutritional_values()
        self.assertTrue(cache.get(cache_mapper.get_nutritional_info(nutritional_object)))
        meal_item.delete()
        self.assertFalse(cache.get(cache_mapper.get_nutritional_info(nutritional_object)))
