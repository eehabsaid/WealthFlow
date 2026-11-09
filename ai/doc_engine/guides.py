class BaseGuideGenerator:
    def __init__(self, model):
        self.model = model

    def filter_model(self):
        return self.model.nodes

    def get_guide_type(self):
        return "base"
        
    def is_technical(self):
        return False

class UserGuideGenerator(BaseGuideGenerator):
    def filter_model(self):
        return [n for n in self.model.nodes if not n.is_admin]

    def get_guide_type(self):
        return "user"

class AdminGuideGenerator(BaseGuideGenerator):
    def filter_model(self):
        return [n for n in self.model.nodes if n.is_admin]

    def get_guide_type(self):
        return "admin"

class TechnicalGuideGenerator(BaseGuideGenerator):
    def filter_model(self):
        return self.model.nodes

    def get_guide_type(self):
        return "technical"
        
    def is_technical(self):
        return True
