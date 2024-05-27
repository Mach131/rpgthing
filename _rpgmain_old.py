from enum import Enum, auto
import traceback
import random

class MainStat(Enum):
  HP = auto()
  MP = auto()
  ATK = auto()
  DEF = auto()
  MAG = auto()
  RES = auto()
  ACC = auto()
  AVO = auto()
  SPD = auto()

class ClassName(Enum):
  WARRIOR = auto()
  ARCHER = auto()
  ROGUE = auto()
  MAGE = auto()
  MERCENARY = auto()
  KNIGHT = auto()
  SNIPER = auto()
  HUNTER = auto()
  ASSASSIN = auto()
  ACROBAT = auto()
  WIZARD = auto()
  SAINT = auto()


class Skill(object):
  def __init__(self, isPassive, isFree):
    self.isPassive = isPassive
    self.isFree = isFree

class GameClass(object):
  def __init__(self, className, parentClass=None, maxRank=3):
    self.className = className
    self.parentClass = parentClass
    self.maxRank = maxRank
    
    self.childClasses = []
    if self.parentClass is not None:
      self.parentClass.childClasses.append(self)

classWarrior = GameClass(ClassName.WARRIOR)
classArcher = GameClass(ClassName.ARCHER)
classRogue = GameClass(ClassName.ROGUE)
classMage = GameClass(ClassName.MAGE)
classMercenary = GameClass(ClassName.MERCENARY, classWarrior, 12)
classKnight = GameClass(ClassName.KNIGHT, classWarrior, 12)
classSniper = GameClass(ClassName.SNIPER, classArcher, 12)
classHunter = GameClass(ClassName.HUNTER, classArcher, 12)
classAssassin = GameClass(ClassName.ASSASSIN, classRogue, 12)
classAcrobat = GameClass(ClassName.ACROBAT, classRogue, 12)
ClassWizard = GameClass(ClassName.WIZARD, classMage, 12)
ClassSaint = GameClass(ClassName.SAINT, classMage, 12)

statValues_base = {
  MainStat.HP: 50,
  MainStat.MP: 30,
  MainStat.ATK: 10,
  MainStat.DEF: 10,
  MainStat.MAG: 10,
  MainStat.RES: 10,
  MainStat.ACC: 50,
  MainStat.AVO: 50,
  MainStat.SPD: 20
}

statValues_perLevel = {
  MainStat.HP: 50,
  MainStat.MP: 10,
  MainStat.ATK: 5,
  MainStat.DEF: 10,
  MainStat.MAG: 5,
  MainStat.RES: 10,
  MainStat.ACC: 10,
  MainStat.AVO: 10,
  MainStat.SPD: 5
}

def getStatSelection(inputString):
  statStrings = inputString.split(" ")
  results = []
  for statString in statStrings:
    if statString == '':
      continue
    try:
      results.append(MainStat[statString.upper()])
    except KeyError:
      print(f"Unrecognized stat: '{statString}'")
  return results

class Player(object):
  def __init__(self, gameClass, level=0, rank_map={}, stat_map={}):
    self.level = level
    self.gameClass = gameClass

    self.statLevels = {}
    for stat in MainStat:
      self.statLevels[stat] = stat_map.get(stat, 0)
    
    self.classRanks = {}
    for className in ClassName:
      self.classRanks[className] = rank_map.get(className, 0)

  def getAllBaseStatValues(self):
    statMap = {stat: self.getBaseStatValue(stat) for stat in MainStat}
    return f"""HP: {statMap[MainStat.HP]}, MP: {statMap[MainStat.MP]}
ATK: {statMap[MainStat.ATK]}, DEF: {statMap[MainStat.DEF]}, MAG: {statMap[MainStat.MAG]}, RES: {statMap[MainStat.RES]}
ACC: {statMap[MainStat.ACC]}, AVO: {statMap[MainStat.AVO]}, SPD: {statMap[MainStat.SPD]}"""

  def getBaseStatValue(self, stat):
    return statValues_base[stat] + (statValues_perLevel[stat] * self.statLevels[stat])

  def levelUpStats(self, randomStats=False):
    if (self.level >= 20):
      print("You have already reached the maximum level.")
      return

    self.level += 1
    print(f"Reached level {self.level}.")

    chosenStats = set()
    while len(chosenStats) < 5:
      print(f"Select {5 - len(chosenStats)} stats to increase.")
      if not randomStats:
        selections = getStatSelection(input(">> "))
      else:
        selections = random.sample(list(MainStat), 5)

      for selection in selections:
        if selection in chosenStats:
          print(f"You have already chosen {selection.name} for this level.")
        else:
          chosenStats.add(selection)
          if len(chosenStats) >= 5:
            break
    print("Increased stats:")
    for stat in MainStat:
      if stat in chosenStats:
        oldStat = self.getBaseStatValue(stat)
        self.statLevels[stat] += 1
        newStat = self.getBaseStatValue(stat)
        print(f"- {stat.name} ({oldStat} -> {newStat})")

  def randomLevel(self):
    self.levelUpStats(True)

def calcDamage(offensiveStat, defensiveStat, rng=True):
  r = random.uniform(0.9, 1.1) if rng else 1
  return int(((offensiveStat ** 1.5)/(defensiveStat ** 0.5)) * r)

def calcAccuracy(acc, avo, distance):
  dist_mod = 1.1 - (0.1 * (distance ** 2))
  return ((acc * dist_mod)/avo) ** 0.5

def compareSpeeds(spd1, spd2):
  return (spd1 ** 0.5)/(spd2 ** 0.5)

def sampleAttacks(p1, p2, isPhysical, sampleDist=1, sampleCount=10):
  os = p1.getBaseStatValue(MainStat.ATK) if isPhysical else p1.getBaseStatValue(MainStat.MAG)
  ds = p2.getBaseStatValue(MainStat.DEF) if isPhysical else p2.getBaseStatValue(MainStat.RES)
  hc = [calcAccuracy(p1.getBaseStatValue(MainStat.ACC), p2.getBaseStatValue(MainStat.AVO), d) for d in range(4)]
  sr = compareSpeeds(p1.getBaseStatValue(MainStat.SPD), p2.getBaseStatValue(MainStat.SPD))
  print(f"Avg damage: {calcDamage(os, ds, False)}; hit chance: {hc}, speed ratio: {sr}")

  sampleResults = []
  for i in range(sampleCount):
    if random.random() >= hc[sampleDist]:
      sampleResults.append("Missed")
    else:
      sampleResults.append(calcDamage(os, ds))
  print(f"Sample Attacks: {sampleResults}")

if __name__ == '__main__':
  p1 = Player(classWarrior)
  p2 = Player(classArcher)

  while True:
    inp = input("> ")
    if inp == "exit":
      break
    try:
      print(eval(inp))
    except Exception:
      print(traceback.format_exc())