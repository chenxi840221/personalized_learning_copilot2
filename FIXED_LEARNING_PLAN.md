# Learning Plan Activity Generation Fix

I've identified and fixed the issue with learning plans not generating activities for the entire period.

## Problem
When creating a learning plan for extended periods (like one month), the system was artificially capping activity generation to only the first 14 days, regardless of the total period length.

In the original code, there was a limitation:
```python
# For very long periods, limit the number of days for activities to keep the plan manageable
activity_days = min(days, 14) if days > 14 else days
```

This meant that a one-month (30-day) learning plan would only have activities for days 1-14, leaving days 15-30 without any scheduled activities.

## Solution
The fix implemented uses the same approach that was already working correctly in the profile-based route. Now, the system:

1. Calculates the total number of weeks in the learning period
2. Generates activities week by week using 7-day segments
3. Adjusts the day numbers to be relative to the full learning period
4. Combines all activities into a comprehensive plan

The updated code now looks like this:
```python
# For very long periods, split into weeks and generate activities for all days
weeks_in_period = (days + 6) // 7  # Ceiling division to get full weeks
all_activities = []
logger.info(f"Creating plan with {weeks_in_period} weeks for learning period: {period.value} ({days} days)")

# Generate a plan for each week of the learning period
for week_num in range(weeks_in_period):
    week_plan_dict = await plan_generator.generate_plan(
        student=user,
        subject=subject,
        relevant_content=relevant_content,
        days=7,  # Always use 7 days for a weekly plan
        is_weekly_plan=True
    )
    
    # Adjust day numbers to be relative to the entire learning period
    week_activities = week_plan_dict.get("activities", [])
    for activity in week_activities:
        # Update day number to be relative to the full learning period
        activity["day"] = activity["day"] + (week_num * 7)
        all_activities.append(activity)
```

## Testing
After implementing this fix, learning plans will now generate activities for the entire period requested, providing a complete learning experience for the entire month or other selected periods.

## Files Modified
- `/backend/api/learning_plan_routes.py` 

To apply this fix, restart the server after implementing the changes.