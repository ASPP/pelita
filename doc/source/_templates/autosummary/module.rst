{{ fullname }}
{{ underline }}

.. automodule:: {{ fullname }}

   {% if pelita_member_filter(fullname, functions) %}
   .. rubric:: Functions

   .. autosummary::
      :toctree:
   {% for item in pelita_member_filter(fullname, functions) %}
      ~{{ item }}
   {%- endfor %}
   {% endif %}

   {% if pelita_member_filter(fullname, classes) %}
   .. rubric:: Classes

   .. autosummary::
      :toctree:
   {% for item in pelita_member_filter(fullname, classes) %}
      ~{{ item }}
   {%- endfor %}
   {% endif %}

   {% if pelita_member_filter(fullname, exceptions) %}
   .. rubric:: Exceptions

   .. autosummary::
      :toctree:
   {% for item in pelita_member_filter(fullname, exceptions) %}
      ~{{ item }}
   {%- endfor %}
   {% endif %}
