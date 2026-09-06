from django import forms
from .models import Contract, ContractVersion, ContractCategory, ContractAssignment
from accounts.models import User, Department


class ContractForm(forms.ModelForm):
    class Meta:
        model  = Contract
        fields = [
            "title", "contract_type", "description",
            "party_name", "party_contact", "party_email", "party_phone",
            "department", "owner",
            "start_date", "end_date", "renewal_date",
            "contract_value", "payment_terms",
            "priority", "notes", "renewal_terms",
        ]
        widgets = {
            "title":          forms.TextInput(attrs={"class": "form-control"}),
            "contract_type":  forms.Select(attrs={"class": "form-select"}),
            "description":    forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "party_name":     forms.TextInput(attrs={"class": "form-control"}),
            "party_contact":  forms.TextInput(attrs={"class": "form-control"}),
            "party_email":    forms.EmailInput(attrs={"class": "form-control"}),
            "party_phone":    forms.TextInput(attrs={"class": "form-control"}),
            "department":     forms.Select(attrs={"class": "form-select"}),
            "owner":          forms.Select(attrs={"class": "form-select"}),
            "start_date":     forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date":       forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "renewal_date":   forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "contract_value": forms.NumberInput(attrs={"class": "form-control"}),
            "payment_terms":  forms.TextInput(attrs={"class": "form-control"}),
            "priority":       forms.Select(attrs={"class": "form-select"}),
            "notes":          forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "renewal_terms":  forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = User.objects.filter(
            status=User.Status.ACTIVE
        ).order_by("username")


class ContractVersionForm(forms.ModelForm):
    class Meta:
        model  = ContractVersion
        fields = ["document", "change_summary"]
        widgets = {
            "document":      forms.FileInput(attrs={"class": "form-control"}),
            "change_summary": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class AssignmentForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(status=User.Status.ACTIVE).order_by("username"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )


class ContractCategoryForm(forms.ModelForm):
    class Meta:
        model  = ContractCategory
        fields = ["name", "description"]
        widgets = {
            "name":        forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
