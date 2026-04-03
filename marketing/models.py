from django.db import models
import uuid

# Create your models here.
class MarketingHeros(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    titre = models.CharField(max_length=255)
    subtitle = models.TextField(blank=True)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="marketing/photos/")
    link = models.CharField(null=True, blank=True)
    btn_text = models.CharField(null=True, max_length=255, blank=True,default="Découvrir")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name
    
# class MarketingCampaign(models.Model):
#     name = models.CharField(max_length=255)
#     start_date = models.DateField()
#     end_date = models.DateField()
#     budget = models.DecimalField(max_digits=10, decimal_places=2)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)


#     def __str__(self):
#         return self.name
# class Advertisement(models.Model):
#     title = models.CharField(max_length=255)
#     content = models.TextField()
#     campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name='advertisements')
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.title
# class Lead(models.Model):
#     name = models.CharField(max_length=255)
#     email = models.EmailField()
#     phone_number = models.CharField(max_length=20, blank=True, null=True)
#     interested_in = models.CharField(max_length=255)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.name
# class SocialMediaPost(models.Model):
#     platform = models.CharField(max_length=100)
#     content = models.TextField()
#     post_date = models.DateTimeField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.platform} - {self.post_date.strftime('%Y-%m-%d')}"
# class EmailCampaign(models.Model):
#     subject = models.CharField(max_length=255)
#     body = models.TextField()
#     sent_date = models.DateTimeField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.subject
# class AnalyticsReport(models.Model):
#     report_name = models.CharField(max_length=255)
#     generated_on = models.DateTimeField(auto_now_add=True)
#     data = models.JSONField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.report_name
# class CustomerFeedback(models.Model):
#     customer_name = models.CharField(max_length=255)
#     feedback = models.TextField()
#     rating = models.IntegerField()
#     submitted_on = models.DateTimeField(auto_now_add=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.customer_name} - {self.rating}"
# class PromotionCode(models.Model):
#     code = models.CharField(max_length=50, unique=True)
#     discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
#     valid_from = models.DateField()
#     valid_to = models.DateField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.code
# class Event(models.Model):
#     event_name = models.CharField(max_length=255)
#     event_date = models.DateTimeField()
#     location = models.CharField(max_length=255)
#     description = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.event_name
# class Partnership(models.Model):
#     partner_name = models.CharField(max_length=255)
#     contact_info = models.TextField()
#     agreement_details = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.partner_name
# class MarketResearch(models.Model):
#     research_topic = models.CharField(max_length=255)
#     findings = models.TextField()
#     conducted_on = models.DateField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.research_topic
# class BrandingAsset(models.Model):
#     asset_name = models.CharField(max_length=255)
#     asset_type = models.CharField(max_length=100)
#     file = models.FileField(upload_to='branding_assets/')
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.asset_name
# class InfluencerCollaboration(models.Model):
#     influencer_name = models.CharField(max_length=255)
#     platform = models.CharField(max_length=100)
#     collaboration_details = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.influencer_name
# class ContentCalendar(models.Model):
#     title = models.CharField(max_length=255)
#     content_type = models.CharField(max_length=100)
#     scheduled_date = models.DateField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.title
# class SEOKeyword(models.Model):
#     keyword = models.CharField(max_length=255, unique=True)
#     search_volume = models.IntegerField()
#     competition_level = models.CharField(max_length=100)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.keyword
# class AdPerformanceMetric(models.Model):
#     ad_title = models.CharField(max_length=255)
#     impressions = models.IntegerField()
#     clicks = models.IntegerField()
#     conversions = models.IntegerField()
#     recorded_on = models.DateField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.ad_title
# class CustomerSegment(models.Model):
#     segment_name = models.CharField(max_length=255)
#     description = models.TextField()
#     criteria = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.segment_name
# class MarketingBudgetAllocation(models.Model):
#     department = models.CharField(max_length=255)
#     allocated_budget = models.DecimalField(max_digits=10, decimal_places=2)
#     fiscal_year = models.CharField(max_length=9)  # e.g., "2023-2024"
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.department} - {self.fiscal_year}"
# class CompetitorAnalysis(models.Model):
#     competitor_name = models.CharField(max_length=255)
#     strengths = models.TextField()
#     weaknesses = models.TextField()
#     analysis_date = models.DateField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.competitor_name
# class MarketingStrategy(models.Model):
#     strategy_name = models.CharField(max_length=255)
#     objectives = models.TextField()
#     tactics = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.strategy_name
# class CustomerJourneyMap(models.Model):
#     stage_name = models.CharField(max_length=255)
#     description = models.TextField()
#     touchpoints = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.stage_name
# class MarketingKPI(models.Model):
#     kpi_name = models.CharField(max_length=255)
#     target_value = models.DecimalField(max_digits=10, decimal_places=2)
#     actual_value = models.DecimalField(max_digits=10, decimal_places=2)
#     measurement_date = models.DateField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.kpi_name
# class MarketingTeamMember(models.Model):
#     name = models.CharField(max_length=255)
#     role = models.CharField(max_length=255)
#     email = models.EmailField()
#     phone_number = models.CharField(max_length=20, blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.name
# class MarketingTool(models.Model):
#     tool_name = models.CharField(max_length=255)
#     purpose = models.TextField()
#     subscription_details = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.tool_name
    