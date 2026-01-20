from src.convert import ReadmeGenerator
class Dummy:
    def __init__(self, p):
        self.pipeline_image = p

rg = ReadmeGenerator()
# single
print('SINGLE:', rg._generate_pipeline_cell(Dummy('figures/LIN.png')))
# multiple
print('MULTI:', rg._generate_pipeline_cell(Dummy('figures/LIN.png;figures/other.jpg')))
# more than three (only first three used if exist)
print('MORE:', rg._generate_pipeline_cell(Dummy('figures/a.png;figures/b.png;figures/c.png;figures/d.png')))
