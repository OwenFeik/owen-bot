
class Card:
    def __init__(self,names,uris,price):
        self.names=names
        self.uris=uris
        if len(self.uris)>1:
            self.dfc=True
        else:
            self.dfc=False
        if price:
            self.price='$'+price
        else:
            self.price='Price N/A'

        

    @property
    def name(self):
        return self.names[0]
    
    @property
    def uri(self):
        return self.uris[0]

    @property
    def back_uri(self):
        if self.dfc:
            return self.uris[1]
        else:
            return False
    @property
    def back_name(self):
        if self.dfc:
            return self.names[1]
        else:
            return False