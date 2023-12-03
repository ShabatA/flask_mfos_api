from ..utils.db import db

class Regions(db.Model):
    __tablename__ = 'regions'

    regionID = db.Column(db.Integer, primary_key=True)
    regionName = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<Region {self.regionID} {self.regionName}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, regionID):
        return cls.query.get_or_404(regionID)
    
    @classmethod
    def get_all_regions(cls):
        regions = cls.query.all()
        return [region.regionName for region in regions]
    