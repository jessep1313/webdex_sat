from django import forms

class PeticionSatForm(forms.Form):
    TIPO_CHOICES = [
        ('R', 'Recibidas'),
        ('E', 'Emitidas'),
    ]
    tipo = forms.ChoiceField(choices=TIPO_CHOICES, label='Tipo', widget=forms.Select(attrs={'class': 'form-select'}))
    fechainicio = forms.DateField(
        label="Fecha inicio",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    fechafinal = forms.DateField(
        label="Fecha final",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        
    )


class FechasForm(forms.Form):
    fecha_inicio = forms.DateField(
        label="Fecha inicio",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    fecha_fin = forms.DateField(
        label="Fecha fin",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )