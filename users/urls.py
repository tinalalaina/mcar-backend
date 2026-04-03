from django.urls import path
from users import views

urlpatterns = [
    path("register-with-otp/", views.UserRegistrationView.as_view(), name="register"),
    path("register/", views.WithOutUserRegistrationView.as_view(), name="register_without_otp"),
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("token/refresh/", views.CustomTokenRefreshView.as_view(), name="token_refresh"),

    path("profile/", views.UserProfileView.as_view(), name="profile"),
    path("profile/photo/", views.UserProfilePhotoView.as_view(), name="profile-photo-self"),
    path("profile/<uuid:user_id>/", views.UserProfileView.as_view(), name="profile-update"),
    path("profile/<uuid:user_id>/photo/", views.UserProfilePhotoView.as_view(), name="profile-update-photo"),

    path("signup/", views.signup, name="signup"),

    path("otp/request/", views.OTPRequestView.as_view(), name="otp_request"),
    path("otp/verify/", views.OTPVerifyView.as_view(), name="otp_verify"),

    path("password/reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path("password/change/", views.ChangePasswordView.as_view(), name="password_change"),

    path("request-reset-password", views.RequestResetPasswordView.as_view(), name="request_reset_password"),
    path("reset-password/<str:uidb64>/<str:token>", views.reset_password, name="reset_password"),

    path("users-all/", views.UserListView.as_view(), name="user_list"),
    path("delete-non-admin/", views.DeleteNonAdminUsersView.as_view(), name="delete_non_admin_users"),
    path("users/delete-non-admin/", views.DeleteNonAdminUsersView.as_view(), name="delete_non_admin_users_legacy"),
    path("users-prestataire/", views.get_prestataire_users, name="get_prestataire_users"),
    path("users-client/", views.get_client_users, name="get_client_users"),
    path("users-support/", views.get_support_users, name="get_support_users"),
    path("user-info/", views.UserInfoView.as_view(), name="user_info"),
]