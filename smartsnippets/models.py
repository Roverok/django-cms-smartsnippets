from django.db import models
from django.core.exceptions import ValidationError
from django.template import Template, TemplateSyntaxError, \
                            TemplateDoesNotExist, VariableNode, loader
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _

from cms.models import CMSPlugin

class SmartSnippet(models.Model):
    name = models.CharField(unique=True, max_length=255)
    template_code = models.TextField(_("Template code"), blank=True)
    template_path = models.CharField(_("Template path"), max_length=100, blank=True, \
        help_text=_('Enter a template (i.e. "snippets/plugin_xy.html") which will be rendered.'))
    sites = models.ManyToManyField(Site, null=False, blank=True,
        help_text=_('Select on which sites the snippet will be available.'),
        verbose_name='sites')
    
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Smart Snippet'
        verbose_name_plural = 'Smart Snippets'

    def get_template(self):
        if self.template_path:
            return loader.get_template(self.template_path)
        else:
            return Template(self.template_code)

    def clean_template_code(self):
        try:
            self.get_template()
        except (TemplateSyntaxError, TemplateDoesNotExist), e:
            raise ValidationError(str(e))

    def render(self, context):
        return self.get_template().render(context)

    def __unicode__(self):
        return self.name


class SmartSnippetVariable(models.Model):
    name = models.CharField(max_length=50,
            help_text=_('Enter the name of the variable defined in the smart snippet template.'))
    widget = models.CharField(max_length=50,
            help_text=_('Select the type of the variable defined in the smart snippet template.'))
    snippet = models.ForeignKey(SmartSnippet, related_name="variables")
    
    class Meta:
        unique_together = (('snippet', 'name'))
        ordering = ['name']
        verbose_name = "Standard variable"

    def save(self, *args, **kwargs):
        super(SmartSnippetVariable, self).save(*args, **kwargs)
        smartsnippet_pointers = self.snippet.smartsnippetpointer_set.all()
        for spointer in smartsnippet_pointers:
            v, _ = Variable.objects.get_or_create(snippet=spointer, snippet_variable=self)
            v.save()
    
    def __unicode__(self):
        return self.name
        
        
class SmartSnippetPointer(CMSPlugin):
    snippet = models.ForeignKey(SmartSnippet)

    def render(self, context):
        vars = dict((var.snippet_variable.name, var.value) for var in self.variables.all())
        context.update(vars)
        return self.snippet.render(context)

    def __unicode__(self):
        return unicode(self.snippet)


class Variable(models.Model):
    snippet_variable = models.ForeignKey(SmartSnippetVariable, related_name='variables')
    value = models.CharField(max_length=1024)
    snippet = models.ForeignKey(SmartSnippetPointer, related_name='variables')

    class Meta:
        unique_together = (('snippet_variable', 'snippet'))
    
    @property
    def name(self):
        return self.snippet_variable.name
    
    @property
    def widget(self):
        return self.snippet_variable.widget
    
    

class DropDownVariable(SmartSnippetVariable):
    choices = models.CharField(max_length=512,
            help_text=_('Enter a comma separated list of choices that will be available in the dropdown variable when adding and configuring the smart snippet on a page.'))
    
    @property
    def choices_list(self):
         return ([choice.strip() for choice in self.choices.split(',') if choice.strip()]
                if self.choices else [])
        
    def save(self, *args, **kwargs):
        self.widget = 'DropDownField'
        super(DropDownVariable, self).save(*args, **kwargs)
