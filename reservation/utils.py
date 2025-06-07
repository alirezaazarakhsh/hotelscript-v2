from django.db.models import Func



class Round(Func):
    function = 'ROUND'
    arity = 2  
    
    
