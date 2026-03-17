from app.database.db import task_collection
from app.utils.helpers import get_period_range
from bson import ObjectId
import pandas as pd


class AnalyticsService:

    # # todo
    @staticmethod
    async def get_user_stats(user_id: str):

        user_object_id = ObjectId(user_id)


        total_tasks = await task_collection.count_documents({
            "created_by": user_object_id
        }) 

        
        completed_tasks = await task_collection.count_documents({
            "created_by": user_object_id,
            "status": "completed"
        })


        pending_tasks = await task_collection.count_documents({
            "created_by": user_object_id,
            "status": "pending"
        })
        
        in_progress_tasks = await task_collection.count_documents({
            "created_by": user_object_id,
            "status": "in_progress"
        })

        cancelled_tasks = await task_collection.count_documents({
            "created_by": user_object_id,
            "status": "cancelled"
        })

        completion_rate = completed_tasks / total_tasks * 100 if total_tasks > 0 else 0

        return {
            "created_by": user_id,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "In_progress_tasks": in_progress_tasks,
            "cancelled_task": cancelled_tasks,
            "completion_rate": completion_rate
        }


    async def get_dashboard_stats(period: str):

        start_date, end_date = get_period_range(period)

        total_tasks = await task_collection.count_documents({
        "created_at": {"$gte": start_date, "$lte": end_date}
        })

        completed_tasks = await task_collection.count_documents({
        "created_at": {"$gte": start_date, "$lte": end_date},
        "status": "completed"
        })

        pending_tasks = await task_collection.count_documents({
        "created_at": {"$gte": start_date, "$lte": end_date},
        "status": "pending"
        })

        in_progress_tasks = await task_collection.count_documents({
        "created_at": {"$gte": start_date, "$lte": end_date},
        "status": "in_progress"
        })

        cancelled_tasks = await task_collection.count_documents({
        "created_at": {"$gte": start_date, "$lte": end_date},
        "status": "cancelled"
        })

        pipeline = [
            {"$match":
              {"created_at": {"$gte": start_date, "$lte": end_date}}
            },
          {
            "$group": {
              "_id": "$priority",
              "count": {"$sum": 1}
        }
       }
        ]

        priority_stats = await task_collection.aggregate(pipeline).to_list(length=None)


        return {
        "period": period,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "In_progress_tasks": in_progress_tasks,
        "Cancelled_task": cancelled_tasks,
        "priority_status":priority_stats
        }  
    

    async def user_analytics():

        #if having 1 million data it shouldn't be done 
        tasks = await task_collection.find({}, {"_id":0}).to_list(length=None)

        df = pd.DataFrame(tasks)

        status_counts = df["status"].value_counts().to_dict()

        # todo
        df = df[df["completed_at"].notna()]

        df["created_at"] = pd.to_datetime(df["created_at"])
        df["completed_at"] = pd.to_datetime(df["completed_at"])

        tasks_per_day = df.groupby(df["created_at"].dt.date).size().to_dict()
        tasks_completed_per_day = df.groupby(df["completed_at"].dt.date).size().to_dict()
       

        df["time_spent"] = df["completed_at"] - df["created_at"]

        avg_time = df["time_spent"].mean().total_seconds()

        return {
            "avg_time":avg_time,
            "status_counts":status_counts,
            "tasks_per_day":tasks_per_day,
            "tasks_completed_per_day":tasks_completed_per_day
        }
    
   



   