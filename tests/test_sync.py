import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sync import player, normalize

class ProjectionTests(unittest.TestCase):
    def stats(self, source, year, values):
        return {'statSourceId':source,'seasonId':year,'statSplitTypeId':0,'scoringPeriodId':0,'stats':values}
    def test_league_weights_and_blend(self):
        p={'id':1,'fullName':'Test','stats':[self.stats(1,2027,{'0':100,'11':10,'42':20}),self.stats(0,2026,{'0':80,'11':20,'42':20})]}
        result=player(p,2027,{0:1,11:-2})
        self.assertEqual(result['projection'],80)
        self.assertEqual(result['ppg'],4)
        self.assertEqual(result['blend'],70)
    def test_missing_not_zero(self):
        self.assertIsNone(player({'id':1,'stats':[]},2027,{0:1})['projection'])
        self.assertIsNone(player({'id':1,'stats':[self.stats(1,2027,{'42':82})]},2027,{0:1})['projection'])
    def test_ignore_wrong_season_split_and_period(self):
        s=self.stats(1,2027,{'0':99});s['scoringPeriodId']=2
        self.assertIsNone(player({'id':1,'stats':[s,self.stats(1,2026,{'0':100})]},2027,{0:1})['projection'])
    def test_allowlist_removes_owner_and_credentials(self):
        league={'id':1,'settings':{'name':'Test','scoringSettings':{'scoringType':'H2H_POINTS','scoringItems':[{'statId':0,'points':1}]}},'teams':[{'id':2,'name':'Team','owners':['secret'],'roster':{'entries':[]}}],'members':[{'email':'private'}],'status':{'currentMatchupPeriod':1},'draftDetail':{'picks':[{'memberId':'secret','playerId':1,'teamId':2} ]}}
        result=normalize(league,[],2027,2)
        self.assertNotIn('members',result)
        self.assertNotIn('owners',result['teams'][0])
        self.assertNotIn('memberId',result['draft']['picks'][0])
    def test_category_league_rejected(self):
        with self.assertRaises(ValueError): normalize({'settings':{'scoringSettings':{'scoringType':'H2H_CATEGORY'}}},[],2027,2)
if __name__=='__main__': unittest.main()
