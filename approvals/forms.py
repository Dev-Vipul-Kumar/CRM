from django import forms
from .models import Approval


class ApprovalActionForm(forms.Form):
    ACTION_CHOICES = [
        (Approval.Action.APPROVED,          "Approve"),
        (Approval.Action.REJECTED,          "Reject"),
        (Approval.Action.CHANGES_REQUESTED, "Request Changes"),
    ]
    action  = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.RadioSelect)
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
    )


class SubmitForReviewForm(forms.Form):
    comment = forms.CharField(
        required=False,
        label="Submission Note",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
