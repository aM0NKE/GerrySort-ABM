import random
import uuid

import mesa
import mesa_geo as mg

from .agents import PersonAgent, RegionAgent
from .space import Nuts2Eu


class GeoSchellingPoints(mesa.Model):
    def __init__(self, red_percentage=0.5, similarity_threshold=0.5):
        super().__init__()

        self.red_percentage = red_percentage
        PersonAgent.SIMILARITY_THRESHOLD = similarity_threshold

        self.schedule = mesa.time.RandomActivation(self)
        self.space = Nuts2Eu()

        self.datacollector = mesa.DataCollector(
            {"unhappy": "unhappy", "happy": "happy",
             "red_districts": "red_districts", "blue_districts": "blue_districts"}
        )

        # Set up the grid with patches for every NUTS region
        ac = mg.AgentCreator(RegionAgent, model=self)
        regions = ac.from_file(
            "data/MN_precincts_initial.geojson", unique_id="district"
        )
        self.space.add_regions(regions)

        for region in regions:
            print(region.__dict__)
            region.init_num_people
            for _ in range(region.init_num_people):
                person = PersonAgent(
                    unique_id=uuid.uuid4().int,
                    model=self,
                    crs=self.space.crs,
                    geometry=region.random_point(),
                    is_red=region.PRES16D / (region.PRES16D + region.PRES16R) < random.random(),
                    region_id=region.unique_id,
                )
                self.space.add_person_to_region(person, region_id=region.unique_id)
                self.schedule.add(person)

        self.datacollector.collect(self)

    @property
    def unhappy(self):
        num_unhappy = 0
        for agent in self.space.agents:
            if isinstance(agent, PersonAgent) and agent.is_unhappy:
                num_unhappy += 1
        return num_unhappy

    @property
    def happy(self):
        return self.space.num_people - self.unhappy
    
    @property
    def red_districts(self):
        num_red = 0
        for region in self.space.agents:
            if isinstance(region, RegionAgent) and region.red_pct > 0.5:
                num_red += 1
        return num_red
    
    @property
    def blue_districts(self):
        num_blue = 0
        for region in self.space.agents:
            if isinstance(region, RegionAgent) and region.red_pct < 0.5:
                num_blue += 1
        return num_blue

    def step(self):
        self.schedule.step()
        self.datacollector.collect(self)

        if not self.unhappy:
            self.running = False